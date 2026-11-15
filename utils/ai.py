"""
utils/ai.py
Gemini 에 질문을 보내고 답을 조각조각 받아 온다 (화면에 바로 흘려 보여 주기 위해).
보내기 전에 가족 이름을 '사람1/사람2' 로 바꾸고, 받은 답에서 다시 이름으로 되돌린다.
"""
import json
import os
import time

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
# 앞에서부터 되는 것을 쓴다. 2026-11-15 에 "안녕" 으로 잰 첫 글자 시간: 3.5 Flash-Lite 1.1초, 2.5 Flash 1.0초,
# 3.6 Flash 5.7초, 3.8 Flash 는 붐벼서 4초 뒤 503. 숫자 계산은 앱이 하므로 빠른 모델을 먼저 쓴다.
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.6-flash", "gemini-3.8-flash"]
TIP_MODELS = MODELS
SKIP_SEC = 300
_SKIP_UNTIL = {}   # 방금 실패한 모델 → 이 시각까지는 건너뛴다 (붐비는 모델에 매번 몇 초씩 쓰지 않게)
_NO_FAST = set()   # 생각 줄이기 설정을 거절한 모델 (다음부터는 설정 없이 보낸다)
ALIASES = {"준영": "사람1", "지윤": "사람2"}

SYSTEM = """너는 한 가족의 가계부 앱 안에 있는 점검·조언 도우미다.
아래 [자료]는 앱이 계산한 월별 합계와 점검 결과다. 이 자료만 근거로 답한다.

규칙
- 쉬운 한국어로 짧게. 결론 먼저, 필요하면 짧은 목록.
- 금액은 자료에 있는 숫자를 그대로 쓴다. 자료에 없는 숫자를 지어내지 않는다. 모르면 모른다고 한다.
- 이상값·미입력은 [앱이 규칙으로 찾은 점검 결과]를 기준으로 설명한다. 잘못이라고 단정하지 말고 "확인해 보세요"라고 한다.
- 사람은 자료에 적힌 대로 '사람1', '사람2' 라고만 부른다.
- 조언은 가계 관리 방향(지출 흐름, 저축 비율, 입력 습관, 목표 대비 상태)까지만 한다.
  특정 종목·상품을 사거나 팔라고 권하지 않는다.
- 너는 값을 읽기만 한다. 입력·수정은 사용자가 앱 화면에서 직접 해야 한다고 안내한다.
"""


class AIError(Exception):
    """사용자에게 그대로 보여 줄 수 있는 쉬운 오류 글"""


def api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def hide_names(text: str) -> str:
    for name, alias in ALIASES.items():
        text = text.replace(name, alias)
    return text


def _show_names(chunks):
    """답 조각에서 '사람1' → 이름. 별명이 조각 경계에 걸려도 바뀌게 끝 글자를 잠깐 붙잡아 둔다."""
    buf = ""
    for c in chunks:
        buf += c
        for name, alias in ALIASES.items():
            buf = buf.replace(alias, name)
        hold = 2 if buf.endswith("사람") else 1 if buf.endswith("사") else 0
        if len(buf) > hold:
            yield buf[:len(buf) - hold]
            buf = buf[len(buf) - hold:]
    if buf:
        yield buf


def _raw_stream(model: str, key: str, body: dict, timeout: float = 60):
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=min(timeout, 10))) as http:
        with http.stream("POST", API.format(model=model), headers={"x-goog-api-key": key}, json=body) as r:
            if r.status_code != 200:
                r.read()
                raise httpx.HTTPStatusError(str(r.status_code), request=r.request, response=r)
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:])
                except ValueError:
                    continue
                for cand in data.get("candidates") or []:
                    for part in (cand.get("content") or {}).get("parts") or []:
                        if part.get("text") and not part.get("thought"):
                            yield part["text"]


def _fast(model: str):
    """답하기 전 '생각'을 최소로 줄이는 설정 (첫 글자가 빨리 나오게). 모델 세대마다 이름이 다르다."""
    if model in _NO_FAST:
        return None
    if "2.5" in model:
        return {"thinkingBudget": 0}
    if "3.8" in model:
        return {"thinkingLevel": "low"}      # 3.8 Flash 는 minimal 을 받지 않는다
    return {"thinkingLevel": "minimal"}


def _generate(body: dict, timeout: float = 60, models: list = None):
    """모델을 앞에서부터 써 본다. 없어진 모델(404)·붐비는 모델(500·503)·한도 넘은 모델(429)이면 다음 모델로."""
    key = api_key()
    if not key:
        raise AIError("AI 키(GEMINI_API_KEY)가 없어 AI 답변을 쓸 수 없습니다.")
    models = [m for m in [(os.getenv("GEMINI_MODEL") or "").strip()] + (models or MODELS) if m]
    tries = [m for m in models if _SKIP_UNTIL.get(m, 0) < time.time()] or list(models)
    i = -1
    while i + 1 < len(tries):
        i += 1
        model, got = tries[i], False
        fast = _fast(model)
        req = {**body, "generationConfig": {**body.get("generationConfig", {}), **({"thinkingConfig": fast} if fast else {})}}
        try:
            for chunk in _raw_stream(model, key, req, timeout):
                got = True
                yield chunk
            if not got:
                raise AIError("AI가 빈 답을 보냈습니다. 질문을 바꿔 다시 해 보세요.")
            return
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code == 400 and fast and not got:
                _NO_FAST.add(model)           # 이 모델은 생각 줄이기 설정을 안 받는다 → 설정 없이 한 번 더
                tries.insert(i + 1, model)
                continue
            if code in (404, 429, 500, 503) and not got:
                _SKIP_UNTIL[model] = time.time() + SKIP_SEC
                if i + 1 < len(tries):
                    continue
            if code == 429:
                raise AIError("AI 사용 한도를 넘었습니다. 잠시 뒤에 다시 해 보세요.") from None
            if code in (400, 401, 403):
                raise AIError(f"AI 키가 맞지 않거나 쓸 수 없는 상태입니다 (오류 {code}).") from None
            if code == 503:
                raise AIError("지금 AI 서버가 붐빕니다 (오류 503). 1~2분 뒤에 다시 해 보세요.") from None
            raise AIError(f"AI 서버 오류입니다 (오류 {code}). 잠시 뒤에 다시 해 보세요.") from None
        except httpx.HTTPError:
            if not got and i + 1 < len(tries):
                continue
            raise AIError("AI 서버에 연결하지 못했습니다. 잠시 뒤에 다시 해 보세요.") from None


def ask(summary: str, history: list):
    """history: [{"role": "user"|"assistant", "text": ...}] (마지막이 이번 질문). 답 글 조각을 차례로 내준다."""
    if not api_key():
        raise AIError("AI 키(GEMINI_API_KEY)가 없어 AI 답변을 쓸 수 없습니다.")
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM + "\n[자료]\n" + hide_names(summary)}]},
        "contents": [{"role": "model" if m["role"] == "assistant" else "user",
                      "parts": [{"text": hide_names(m["text"])}]} for m in history],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }
    return _show_names(_generate(body))


TIP_SYSTEM = """너는 가계부 앱 화면 맨 위에 한 줄 조언을 써 주는 도우미다.
아래 [자료]만 근거로, 이 화면을 보는 사람에게 도움이 될 조언을 쓴다.
- 딱 한 줄. 두 문장 이내, 120자 안팎. 줄바꿈·목록·마크다운·이모지 금지.
- 친근한 존댓말. 자료의 숫자(%나 금액)를 1~2개 넣고, 끝에 짧게 방향을 말한다.
- 자료에 없는 숫자를 지어내지 않는다. 특정 종목·상품을 권하지 않는다.
- 사람은 '사람1', '사람2' 라고만 부른다.
"""


def one_line(tab: str, facts: str, timeout: float = 8) -> str:
    """탭 위에 보여 줄 한 줄 조언. 실패하면 AIError."""
    body = {
        "system_instruction": {"parts": [{"text": TIP_SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": f"화면: {tab}\n[자료]\n{hide_names(facts)}"}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
    }
    text = "".join(_show_names(_generate(body, timeout, TIP_MODELS)))
    return " ".join(text.replace("*", "").split())
