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
import extra_streamlit_components as stx
from utils.local_auth import local_storage

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

def get_cookie_manager():
    if "cookie_manager" not in st.session_state:
        st.session_state["cookie_manager"] = stx.CookieManager(key="sb_cookie_manager")
    return st.session_state["cookie_manager"]


@st.cache_resource
def get_supabase_client() -> Client:
    """Supabase 클라이언트 싱글톤 반환"""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        st.error("⚠️ Supabase 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        st.stop()
    return create_client(url, key, options=None)


# ─── 세션 쿠키 & LocalStorage 저장/로드 ────────────────────────────────────

def _save_session(email: str, access_token: str, refresh_token: str) -> bool:
    """로그인 정보를 브라우저 쿠키와 LocalStorage에 이중 저장"""
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.set(_COOKIE_KEY_REFRESH, refresh_token, max_age=30*24*60*60)
        cookie_manager.set(_COOKIE_KEY_EMAIL, email, max_age=30*24*60*60)
    except Exception as e:
        print(f"Cookie save error: {e}")
        
    ls_token_done = False
    ls_email_done = False
    try:
        res_token = local_storage("set", storage_key="sb_refresh_token", value=refresh_token, component_key="ls_set_token")
        if res_token == "set_done": ls_token_done = True
        
        res_email = local_storage("set", storage_key="sb_user_email", value=email, component_key="ls_set_email")
        if res_email == "set_done": ls_email_done = True
    except Exception as e:
        print(f"LocalStorage save error: {e}")
        
    return ls_token_done and ls_email_done


def _load_session() -> dict | None | str:
    """
    저장된 브라우저 쿠키/LocalStorage 로드
    반환값:
    - dict: 로그인 정보 존재
    - "EMPTY": 응답을 받았으나 로그인 정보 없음
    - None: 아직 컴포넌트 응답 대기 중 (Loading)
    """
    try:
        ls_data = local_storage("get_all", component_key="ls_get_all")
        if ls_data is not None:
            # LocalStorage 응답 완료
            if isinstance(ls_data, dict):
                refresh_token = ls_data.get("refresh_token")
                email = ls_data.get("email")
                if refresh_token:
                    return {
                        "email": email,
                        "refresh_token": refresh_token,
                        "source": "local_storage"
                    }
                    
            # LocalStorage에 없으면 Cookie Fallback
            cookie_manager = get_cookie_manager()
            refresh_token = cookie_manager.get(_COOKIE_KEY_REFRESH)
            email = cookie_manager.get(_COOKIE_KEY_EMAIL)
            
            if refresh_token:
                return {
                    "email": email,
                    "refresh_token": refresh_token,
                    "source": "cookie"
                }
                
            return "EMPTY"
    except Exception as e:
        print(f"Session load error: {e}")
        
    return None


def _clear_session_file() -> bool:
    """세션 쿠키 및 LocalStorage 삭제"""
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.delete(_COOKIE_KEY_REFRESH)
        cookie_manager.delete(_COOKIE_KEY_EMAIL)
    except Exception as e:
        print(f"Cookie clear error: {e}")
        
    ls_token_done = False
    ls_email_done = False
    try:
        res_token = local_storage("remove", storage_key="sb_refresh_token", component_key="ls_rem_token")
        if res_token == "remove_done": ls_token_done = True
        
        res_email = local_storage("remove", storage_key="sb_user_email", component_key="ls_rem_email")
        if res_email == "remove_done": ls_email_done = True
    except Exception as e:
        print(f"LocalStorage clear error: {e}")
        
    return ls_token_done and ls_email_done


# ─── 자동 로그인 복원 ────────────────────────────────────────

def try_restore_session() -> bool:
    """저장된 쿠키로 자동 로그인 시도. 성공 시 True."""
    if is_authenticated():
        return True

    saved = _load_session()
    
    if saved is None:
        # 컴포넌트 응답 대기 중: 화면 깜빡임(Flashing) 방지를 위한 로딩 UI
        with st.container():
            st.markdown("<div style='text-align:center; padding:100px; color:#64748b; font-family:sans-serif;'><h4>🔄 자동 로그인 확인 중...</h4></div>", unsafe_allow_html=True)
        st.stop()
        
    if saved == "EMPTY":
        return False

    if isinstance(saved, dict) and saved.get("refresh_token"):
        token = saved["refresh_token"]
        
        if "_bad_tokens" not in st.session_state:
            st.session_state["_bad_tokens"] = set()
            
        if token in st.session_state["_bad_tokens"]:
            _clear_session_file()
            return False

        try:
            client = get_supabase_client()
            # refresh_token으로 세션 갱신
            res = client.auth.refresh_session(token)
            if res.session and res.user:
                st.session_state["user"] = res.user
                st.session_state["access_token"] = res.session.access_token
                # 갱신된 토큰으로 이중 업데이트 (지연 처리)
                st.session_state["_pending_session_save"] = {
                    "email": res.user.email,
                    "access_token": res.session.access_token,
                    "refresh_token": res.session.refresh_token,
                }
                _save_session(res.user.email, res.session.access_token, res.session.refresh_token)
                return True
        except Exception:
            # 토큰 만료 또는 오류 → 정보 삭제
            st.session_state["_bad_tokens"].add(token)
            st.session_state["_pending_session_clear"] = True
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
            # 즉시 저장하지 않고 플래그 세팅 (st.switch_page 등으로 컴포넌트가 무시되는 현상 방지)
            st.session_state["_pending_session_save"] = {
                "email": response.user.email,
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            }
            _save_session(response.user.email, response.session.access_token, response.session.refresh_token)
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
    st.session_state["_pending_session_clear"] = True
    _clear_session_file()


def is_authenticated() -> bool:
    """현재 세션에서 로그인 여부 확인 및 글로벌 스타일링 주입"""
    # ── 지연된 세션 저장 처리 ──
    if "_pending_session_save" in st.session_state:
        data = st.session_state["_pending_session_save"]
        if _save_session(data["email"], data["access_token"], data["refresh_token"]):
            del st.session_state["_pending_session_save"]
            
    if "_pending_session_clear" in st.session_state:
        if _clear_session_file():
            del st.session_state["_pending_session_clear"]
        
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
