import os
import json
import io
import time
import streamlit as st
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

MAX_SIZE = 800
JPEG_QUALITY = 60

_PROMPT = (
    "이 금융앱 캡처 화면에서 계좌명과 보유 종목 데이터를 추출하세요.\n"
    "반드시 아래 JSON 형식만 출력하고 설명이나 마크다운은 절대 쓰지 마세요:\n\n"
    "{\"account_name\": \"계좌명\", \"stocks\": [{\"stock_name\": \"종목명\", "
    "\"quantity\": 수량, \"average_price\": 평단가, \"current_price\": 현재가, "
    "\"principal\": 원금, \"valuation\": 평가액}]}\n\n"
    "account_name은 다음 중 하나: 주택청약/IRP/중개형ISA/청년도약/CMA/KB/TOSS/업비트/총 예수금\n"
    "총 예수금이면 예수금(원화)(qty=1,원금=평가액=원화금액)과 예수금(달러)(qty=달러수량) 포함.\n"
    "모든 숫자는 정수(쉼표 없음), 모르면 0."
)

def _compress(path: str) -> Image.Image | None:
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_SIZE:
            scale = MAX_SIZE / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
        return img
    except Exception as e:
        print(f"[vision] compress error: {e}")
        return None

def analyze_kakao_assets(image_paths: list) -> list | None:
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
        return None

    genai.configure(api_key=api_key)
    # gemini-1.5-flash-8b: 무료 티어 1500RPD / 분당 15회 - 가장 안정적
    model = genai.GenerativeModel("gemini-1.5-flash-8b")

    total = len(image_paths)
    status_box = st.empty()
    progress_bar = st.progress(0)
    errors = []   # 스레드 안에서 st 호출 금지 → 에러를 리스트로 모음
    results = []

    for idx, path in enumerate(image_paths):
        # 두 번째 이미지부터 4초 딜레이 (RPM 한도 초과 방지)
        if idx > 0:
            time.sleep(4)

        # ── 압축 ──
        status_box.info(f"📦 이미지 압축 중... ({idx+1}/{total})")
        progress_bar.progress((idx * 2) / (total * 2 + 1), text=f"📦 압축 {idx+1}/{total}")
        img = _compress(path)
        if img is None:
            errors.append(f"❌ 이미지 {idx+1}: 로드/압축 실패")
            continue

        # ── AI 분석 ──
        status_box.info(f"🤖 AI 분석 중... ({idx+1}/{total}장)")
        progress_bar.progress((idx * 2 + 1) / (total * 2 + 1), text=f"🤖 분석 {idx+1}/{total}")

        raw_text = ""
        success = False
        for attempt in range(3):
            try:
                resp = model.generate_content([_PROMPT, img])
                raw_text = resp.text.strip()
                print(f"[vision] img {idx+1} raw response: {raw_text[:300]}")

                # 마크다운 코드블록 제거
                text = raw_text
                if "```" in text:
                    parts = text.split("```")
                    text = parts[1] if len(parts) > 1 else parts[0]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()

                parsed = json.loads(text)
                results.append(parsed)
                success = True
                break
            except json.JSONDecodeError:
                errors.append(f"⚠️ 이미지 {idx+1} JSON 파싱 실패 (시도 {attempt+1})\nAI 응답: `{raw_text[:300]}`")
                print(f"[vision] JSON parse error, raw: {raw_text[:300]}")
                break   # JSON 오류는 재시도해도 같으므로 바로 포기
            except Exception as e:
                err = str(e)
                print(f"[vision] API error (attempt {attempt+1}): {err[:300]}")
                if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                    wait = 10 * (attempt + 1)
                    status_box.warning(f"⏳ API 한도 초과, {wait}초 대기 후 재시도 ({attempt+1}/3)...")
                    time.sleep(wait)
                else:
                    errors.append(f"❌ 이미지 {idx+1} API 에러: {err[:200]}")
                    break

        if not success and not any(f"이미지 {idx+1}" in e for e in errors):
            errors.append(f"❌ 이미지 {idx+1}: 분석 실패 (3회 시도 모두 실패)")

    # ── 에러 표시 ──
    for err_msg in errors:
        st.warning(err_msg)

    progress_bar.progress(1.0, text="✅ 완료!")
    time.sleep(0.3)
    status_box.empty()
    progress_bar.empty()

    if not results:
        return None

    # 동일 계좌 합산
    merged: dict[str, dict] = {}
    for r in results:
        acc = r.get("account_name", "")
        if not acc:
            continue
        if acc not in merged:
            merged[acc] = {"account_name": acc, "stocks": []}
        existing = {s["stock_name"] for s in merged[acc]["stocks"]}
        for s in r.get("stocks", []):
            if s.get("stock_name") not in existing:
                merged[acc]["stocks"].append(s)

    return list(merged.values()) if merged else None
