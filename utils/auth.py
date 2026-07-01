"""
utils/auth.py
Supabase 인증 관련 유틸리티 + 자동 로그인 (세션 파일 기반)
"""
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json
import pathlib
from datetime import datetime, timezone
from streamlit_cookies_controller import CookieController

load_dotenv()

# Streamlit Cloud 배포 시 st.secrets → os.environ 동기화
try:
    for k, v in st.secrets.items():
        if isinstance(v, str):
            os.environ.setdefault(k, v)
except Exception:
    pass  # 로컬 환경에서는 st.secrets가 없을 수 있음

# 이메일 → 한국어 이름 매핑
EMAIL_TO_NAME = {
    "jypark930@naver.com":  "준영",
    "lovejidbs@naver.com":  "지윤",
}

# 브라우저 쿠키 컨트롤러
_COOKIE_KEY_REFRESH = "sb_refresh_token"
_COOKIE_KEY_EMAIL = "sb_user_email"

def _get_cookie_controller():
    if "cookie_controller" not in st.session_state:
        st.session_state["cookie_controller"] = CookieController()
    return st.session_state["cookie_controller"]


@st.cache_resource
def get_supabase_client() -> Client:
    """Supabase 클라이언트 싱글톤 반환"""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        st.error("⚠️ Supabase 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        st.stop()
    return create_client(url, key, options=None)


# ─── 세션 쿠키 저장/로드 ────────────────────────────────────

def _save_session(email: str, access_token: str, refresh_token: str):
    """로그인 정보를 브라우저 쿠키에 저장"""
    try:
        controller = _get_cookie_controller()
        # 토큰을 30일 동안 유지
        controller.set(_COOKIE_KEY_REFRESH, refresh_token, max_age=30*24*60*60)
        controller.set(_COOKIE_KEY_EMAIL, email, max_age=30*24*60*60)
    except Exception as e:
        print(f"Cookie save error: {e}")


def _load_session() -> dict | None:
    """저장된 브라우저 쿠키 로드"""
    try:
        controller = _get_cookie_controller()
        refresh_token = controller.get(_COOKIE_KEY_REFRESH)
        email = controller.get(_COOKIE_KEY_EMAIL)
        
        if refresh_token:
            return {
                "email": email,
                "refresh_token": refresh_token
            }
    except Exception as e:
        print(f"Cookie load error: {e}")
    return None


def _clear_session_file():
    """세션 쿠키 삭제"""
    try:
        controller = _get_cookie_controller()
        controller.remove(_COOKIE_KEY_REFRESH)
        controller.remove(_COOKIE_KEY_EMAIL)
    except Exception as e:
        print(f"Cookie clear error: {e}")


# ─── 자동 로그인 복원 ────────────────────────────────────────

def try_restore_session() -> bool:
    """저장된 쿠키로 자동 로그인 시도. 성공 시 True."""
    if is_authenticated():
        return True

    saved = _load_session()
    if not saved or not saved.get("refresh_token"):
        return False

    try:
        client = get_supabase_client()
        # refresh_token으로 세션 갱신
        res = client.auth.refresh_session(saved["refresh_token"])
        if res.session and res.user:
            st.session_state["user"] = res.user
            st.session_state["access_token"] = res.session.access_token
            # 갱신된 토큰으로 쿠키 업데이트
            _save_session(
                res.user.email,
                res.session.access_token,
                res.session.refresh_token,
            )
            return True
    except Exception:
        # 토큰 만료 또는 오류 → 쿠키 삭제
        _clear_session_file()
    return False


# ─── 로그인 / 로그아웃 ──────────────────────────────────────

def login(email: str, password: str) -> bool:
    """이메일/패스워드로 로그인, 성공 시 세션 저장"""
    try:
        client = get_supabase_client()
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        if response.session:
            st.session_state["user"] = response.user
            st.session_state["access_token"] = response.session.access_token
            # 자동 로그인용 세션 파일 저장
            _save_session(
                response.user.email,
                response.session.access_token,
                response.session.refresh_token,
            )
            return True
    except Exception as e:
        st.error(f"로그인 실패: {e}")
    return False


def logout():
    """로그아웃 및 세션 초기화"""
    try:
        client = get_supabase_client()
        client.auth.sign_out()
    except Exception:
        pass
    for key in ["user", "access_token"]:
        st.session_state.pop(key, None)
    _clear_session_file()


def is_authenticated() -> bool:
    """현재 세션에서 로그인 여부 확인 및 글로벌 스타일링 주입"""
    st.markdown("""
    <style>
    /* ── 웹 폰트 (KoPubWorld) ── */
    @font-face {
        font-family: 'KoPubWorldBold';
        src: url('/app/static/fonts/kopub_dotum_bold.ttf') format('truetype');
        font-weight: bold;
        font-style: normal;
    }

    * { font-family: 'KoPubWorldBold', -apple-system, BlinkMacSystemFont, sans-serif; }
    .font-orbitron { font-family: 'KoPubWorldBold', monospace !important; }

    .stApp {
        background-color: #f4f5f7 !important;
        color: #1e293b !important;
    }

    /* ── 여백 조율 ── */
    .block-container { padding-top: 4rem !important; }
    h1 {
        transform: translate(18px, -20px) !important;
        color: #0f172a !important;
    }

    /* ── 사이드바 ── */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.03);
    }
    [data-testid="stSidebarNavItems"] li > div[data-testid="stSidebarNavLinkActive"] {
        background: rgba(255, 107, 0, 0.08) !important;
        border-left: 4px solid #ff6b00;
        border-radius: 0 8px 8px 0;
    }
    [data-testid="stSidebarNavItems"] li > div:hover {
        background-color: rgba(255, 107, 0, 0.04) !important;
    }
    [data-testid="stSidebarNav"] ul li a {
        padding: 12px 16px !important;
        border-radius: 8px !important;
        margin-bottom: 4px !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebarNav"] ul li a span {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
    }
    [data-testid="stSidebarNavItems"] li > div[data-testid="stSidebarNavLinkActive"] a span {
        color: #ff6b00 !important;
    }
    [data-testid="stSidebarNav"] ul li a:hover span {
        color: #ff6b00 !important;
    }

    /* ── Streamlit 탭 ── */
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #64748b !important;
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.3s ease;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ff6b00 !important;
        border-bottom: 2px solid #ff6b00 !important;
    }
    button[data-baseweb="tab"]:hover { color: #f26a21 !important; }

    /* ── 입력 필드 ── */
    .stSelectbox > div[data-baseweb="select"] > div,
    .stTextInput > div[data-baseweb="input"] > div,
    .stNumberInput > div[data-baseweb="input"] > div {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        color: #1e293b !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stSelectbox > div[data-baseweb="select"] > div:focus-within,
    .stTextInput > div[data-baseweb="input"] > div:focus-within,
    .stNumberInput > div[data-baseweb="input"] > div:focus-within {
        border-color: #ff6b00 !important;
        box-shadow: 0 0 0 2px rgba(255, 107, 0, 0.2) !important;
    }

    /* ── 메뉴 제거 ── */
    #MainMenu, .stAppDeployButton, button[title="View options"] { display: none !important; }

    /* ── 사이드바 제어 버튼 ── */
    [data-testid="collapsedControl"] svg,
    header[data-testid="stHeader"] button svg { display: none !important; }
    
    [data-testid="collapsedControl"],
    header[data-testid="stHeader"] button {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        width: auto !important; height: auto !important;
        padding: 5px 15px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }
    [data-testid="collapsedControl"]::after,
    header[data-testid="stHeader"] button::after {
        content: "Menu" !important;
        font-family: 'KoPubWorldBold', sans-serif !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #1b263b !important;
        line-height: 1.5 !important;
    }

    /* ── 월 네비게이터 강제 조율 ── */
    div[data-testid="stHorizontalBlock"]:has(.date-col) {
        flex-wrap: nowrap !important;
        gap: 10px !important;
        width: 100% !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.date-col) > div[data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: calc(50% - 5px) !important;
        overflow: hidden !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container #month-nav-marker) {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 10px !important;
        margin-bottom: 10px;
    }
    div[data-testid="stVerticalBlock"]:has(> div.element-container #month-nav-marker) > div.element-container {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0 !important;
    }

        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebarNav"] ul li a span {
        font-size: 1.25rem !important; /* 글자 크기 큼직하게 (약 20px) */
        font-weight: 700 !important;
        line-height: 1.5 !important;
    }
    [data-testid="stSidebarNav"] ul li a:hover {
        background: rgba(0, 242, 254, 0.15) !important;
    }

    /* ── 커스텀 스크롤바 ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #ff6b00; }

    /* ── 데이터프레임 ── */
    [data-testid="stDataFrame"] iframe { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)
    return "user" in st.session_state and st.session_state["user"] is not None


def get_current_user():
    """현재 로그인된 유저 정보 반환"""
    return st.session_state.get("user", None)


def get_current_user_email() -> str:
    """현재 로그인된 유저 이메일 반환"""
    user = get_current_user()
    return user.email if user else ""


def get_current_user_name() -> str:
    """현재 로그인된 유저 한국어 이름 반환 (준영/지윤)"""
    email = get_current_user_email()
    return EMAIL_TO_NAME.get(email, email)
