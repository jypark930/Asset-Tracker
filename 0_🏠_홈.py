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

    /* 전체 배경 (로그인 페이지 전용) */
    [data-testid="stAppViewContainer"] {
        background-color: #f4f5f7;
        min-height: 100vh;
    }

    /* 로그인 카드 */
    .login-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 24px;
        padding: 48px 40px;
        margin: 40px auto;
        max-width: 440px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.04);
    }

    /* 헤더 */
    .login-header {
        text-align: center;
        margin-bottom: 32px;
    }
    .login-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e293b;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .login-subtitle {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: 8px;
    }

    /* 로그인 버튼 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #ff6b00, #ff8c00) !important;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 12px 0 !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(255, 107, 0, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(255, 107, 0, 0.35) !important;
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
    st.switch_page("pages/2_💳_가계부.py")


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
                    st.switch_page("pages/2_💳_가계부.py")

    st.markdown("""
    <div class="login-footer">
        Supabase 계정으로 로그인합니다<br>
        계정이 없다면 Supabase 대시보드에서 사용자를 먼저 생성하세요.
    </div>
    """, unsafe_allow_html=True)
