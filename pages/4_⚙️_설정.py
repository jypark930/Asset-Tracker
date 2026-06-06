"""
pages/4_⚙️_설정.py
계정 정보 및 앱 설정
"""
import streamlit as st

st.set_page_config(page_title="설정 | Asset Tracker", page_icon="⚙️")

from utils.auth import is_authenticated, get_current_user, logout, try_restore_session, EMAIL_TO_NAME

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("app.py")

st.title("⚙️ 설정")

user = get_current_user()
_email = user.email if user else ""
_name  = EMAIL_TO_NAME.get(_email, _email)

# ── 계정 정보 ──────────────────────────────────────────────
st.subheader("👤 계정 정보")
st.text_input("이름",  value=_name,  disabled=True)
st.text_input("이메일", value=_email, disabled=True)


st.divider()

# ── Supabase 연결 상태 ──────────────────────────────────────
st.subheader("🔌 Supabase 연결 상태")
import os
from dotenv import load_dotenv
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL", "")
if supabase_url and "your-project" not in supabase_url:
    st.success(f"✅ 연결됨: {supabase_url}")
else:
    st.error("❌ Supabase URL이 설정되지 않았습니다. .env 파일을 확인하세요.")

st.divider()

# ── 로그아웃 ────────────────────────────────────────────────
st.subheader("🚪 로그아웃")
if st.button("로그아웃", type="primary"):
    logout()
    st.success("로그아웃 되었습니다.")
    st.switch_page("app.py")
