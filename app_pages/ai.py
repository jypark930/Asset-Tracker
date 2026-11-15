"""
app_pages/ai.py  ─  AI 점검: 앱이 찾은 이상값·미입력 → AI 설명·조언 (읽기 전용)
"""
import time

import streamlit as st

from utils.ai import AIError, api_key, ask
from utils.auth import get_supabase_client
from utils.check import build_summary, load_tables, run_checks
from utils.ui import now_kst, page_header, section

MAX_QUESTIONS = 30      # 한 번 접속에서 물을 수 있는 횟수 (무료 한도 보호)
REFRESH_SEC = 120
PRESETS = [
    ("이상한 값 설명", "투자현황에 입력된 값 중에 추이에 비해 이상하게 적거나 많은 값이 있어? 잘못 입력한 것 같은 값을 알려 줘."),
    ("빠진 입력 정리", "입력이 안 된 부분을 달별로 정리해서, 무엇부터 채우면 좋을지 알려 줘."),
    ("마감 조언", "지난달 마감 입력을 끝냈어. 지금 상태를 보고 앞으로 어떻게 관리하면 좋을지 조언해 줘."),
]

page_header("AI 점검", "입력한 값을 점검하고, AI에게 물어볼 수 있어요. AI는 읽기만 합니다.", show_month=False)
now = now_kst()
today = (now.year, now.month)


def _load(force: bool = False):
    c = st.session_state.get("ai_check")
    if force or not c or time.time() - c["at"] > REFRESH_SEC:
        tables = load_tables(get_supabase_client())
        findings = run_checks(tables, today)
        c = {"at": time.time(), "findings": findings, "summary": build_summary(tables, today, findings)}
        st.session_state["ai_check"] = c
    return c


with st.spinner("점검하는 중..."):
    try:
        check = _load()
    except Exception as e:
        st.error(f"값을 불러오지 못했습니다: {e}")
        st.stop()

# ── 점검 결과 (AI 없이 계산) ──────────────────────────────
head, btn = st.columns([5, 1.3], vertical_alignment="center")
with head:
    section("점검 결과", "fact_check")
if btn.button("다시 점검", icon=":material/refresh:", width="stretch"):
    check = _load(force=True)

for kind, title, none_msg in (("odd", "이상해 보이는 값", "이상해 보이는 값이 없습니다."),
                              ("missing", "입력 안 된 곳", "빠진 입력이 없습니다.")):
    items = [f for f in check["findings"] if f["kind"] == kind]
    if not items:
        st.markdown(f"<div class='at-todo ok'>{none_msg}</div>", unsafe_allow_html=True)
        continue
    with st.expander(f"{title} {len(items)}건", expanded=len(items) <= 8, icon=":material/warning:"):
        st.markdown("\n".join(f"- {f['text']}" for f in items))
st.caption("규칙으로 찾은 '확인해 볼 곳'입니다. 큰돈을 넣었거나 뺀 달처럼 실제로 맞는 값일 수도 있어요.")

# ── AI 채팅 ───────────────────────────────────────────────
section("AI에게 물어보기", "forum")
if not api_key():
    st.info("AI 키가 설정되지 않아 지금은 점검 결과만 볼 수 있습니다.", icon=":material/info:")
    st.stop()

msgs = st.session_state.setdefault("ai_msgs", [])


def _preset(q: str):
    st.session_state["ai_pending"] = q


with st.container(horizontal=True, key="ai_presets"):
    for label, q in PRESETS:
        st.button(label, key=f"ai_p_{label}", on_click=_preset, args=(q,))
    if msgs:
        st.button("대화 지우기", key="ai_clear", type="tertiary", on_click=msgs.clear)

for m in msgs:
    with st.chat_message(m["role"]):
        st.markdown(m["text"])

typed = st.chat_input("예: 10월 지출이 평소보다 많았어?")
question = st.session_state.pop("ai_pending", None) or typed
asked = sum(1 for m in msgs if m["role"] == "user")

if question:
    if asked >= MAX_QUESTIONS:
        st.warning(f"한 번 접속에서 {MAX_QUESTIONS}번까지 물을 수 있어요. '대화 지우기'를 누르고 다시 해 보세요.")
    else:
        msgs.append({"role": "user", "text": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                answer = st.write_stream(ask(check["summary"], msgs[-12:]))
                msgs.append({"role": "assistant", "text": answer})
            except AIError as e:
                msgs.pop()
                st.warning(str(e))

st.caption("질문과 월별 합계 숫자가 Google(Gemini)로 전송됩니다. 이름·거래 메모·이메일은 보내지 않고, 대화는 저장하지 않습니다.")
