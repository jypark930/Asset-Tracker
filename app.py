"""
app.py  ─  Asset Tracker 메인 진입점
로그인 여부에 따라 로그인 화면 또는 대시보드로 라우팅
"""
import streamlit as st
from utils.auth import is_authenticated, login, try_restore_session

# ── 페이지 기본 설정 ───────────────────────────────────────
st.set_page_config(
    page_title="Asset Tracker",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── 커스텀 CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    /* 전체 배경 */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        min-height: 100vh;
    }

    /* 로그인 카드 */
    .login-card {
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 48px 40px;
        margin: 40px auto;
        max-width: 440px;
        box-shadow: 0 25px 50px rgba(0,0,0,0.4);
    }

    /* 헤더 */
    .login-header {
        text-align: center;
        margin-bottom: 32px;
    }
    .login-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .login-subtitle {
        color: rgba(255,255,255,0.5);
        font-size: 0.9rem;
        margin-top: 6px;
    }

    /* 입력 필드 */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 12px 16px !important;
        font-size: 0.95rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #a78bfa !important;
        box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.2) !important;
    }
    .stTextInput > label {
        color: rgba(255,255,255,0.75) !important;
        font-weight: 500 !important;
    }

    /* 로그인 버튼 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #7c3aed, #3b82f6) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 12px 0 !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.4) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.6) !important;
    }

    /* 사이드바 숨기기 (로그인 화면) */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }

    /* 푸터 */
    .login-footer {
        text-align: center;
        color: rgba(255,255,255,0.3);
        font-size: 0.78rem;
        margin-top: 24px;
    }

    /* 구분선 색상 */
    hr { border-color: rgba(255,255,255,0.1) !important; }
</style>
""", unsafe_allow_html=True)


# ── 이미 로그인된 경우 또는 자동 로그인 복원 ──────────────
if is_authenticated() or try_restore_session():
    st.switch_page("pages/1_📊_대시보드.py")


# ── 로그인 화면 렌더링 ──────────────────────────────────────
st.markdown("""
<div class="login-card">
    <div class="login-header">
        <p style="font-size:2.5rem; margin:0;">💼</p>
        <h1 class="login-title">Asset Tracker</h1>
        <p class="login-subtitle">가계부 &amp; 투자 현황 한눈에</p>
    </div>
</div>
""", unsafe_allow_html=True)

# 폼을 카드 스타일에 맞게 배치
with st.container():
    email = st.text_input("📧 이메일", placeholder="you@example.com")
    password = st.text_input("🔑 비밀번호", type="password", placeholder="••••••••")

    st.write("")  # spacing

    if st.button("로그인", type="primary", use_container_width=True):
        if not email or not password:
            st.error("이메일과 비밀번호를 모두 입력하세요.")
        else:
            with st.spinner("로그인 중..."):
                if login(email, password):
                    st.success("✅ 로그인 성공!")
                    st.switch_page("pages/1_📊_대시보드.py")

    st.markdown("""
    <div class="login-footer">
        Supabase 계정으로 로그인합니다<br>
        계정이 없다면 Supabase 대시보드에서 사용자를 먼저 생성하세요.
    </div>
    """, unsafe_allow_html=True)
