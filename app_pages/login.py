"""
app_pages/login.py  ─  로그인 화면
"""
import streamlit as st

from utils.auth import login

st.markdown("""
<style>
.at-login-head { text-align:center; margin: 6vh 0 1.2rem; }
.at-login-head .logo { font-size: 2.6rem; color:#3b82f6; }
.at-login-head h1 { font-size: 1.9rem; font-weight: 800; color:#f1f5f9; margin: 0.2rem 0 0; }
.at-login-head p { color:#9ca3af; margin-top: 0.3rem; }
.st-key-glass_login { max-width: 420px; margin: 0 auto; }
</style>
<div class="at-login-head">
  <div class="logo">₩</div>
  <h1>Asset Tracker</h1>
  <p>우리 집 가계부와 자산을 한눈에</p>
</div>
""", unsafe_allow_html=True)

with st.container(border=True, key="glass_login"):
    with st.form("login_form", border=False):
        email = st.text_input("이메일", placeholder="you@example.com", autocomplete="email")
        password = st.text_input("비밀번호", type="password", placeholder="••••••••",
                                 autocomplete="current-password")
        submitted = st.form_submit_button("로그인", type="primary", width="stretch",
                                          icon=":material/login:")
    if submitted:
        if not email or not password:
            st.error("이메일과 비밀번호를 모두 입력하세요.")
        else:
            with st.spinner("로그인 중..."):
                if login(email.strip(), password):
                    st.rerun()
    st.caption("한 번 로그인하면 이 기기에서는 다음부터 자동으로 로그인됩니다.")
