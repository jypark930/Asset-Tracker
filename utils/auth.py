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

# 세션 파일 경로 (앱 디렉토리 내 .session.json)
_SESSION_FILE = pathlib.Path(__file__).parent.parent / ".session.json"


@st.cache_resource
def get_supabase_client() -> Client:
    """Supabase 클라이언트 싱글톤 반환"""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        st.error("⚠️ Supabase 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        st.stop()
    return create_client(url, key, options=None)


# ─── 세션 파일 저장/로드 ────────────────────────────────────

def _save_session(email: str, access_token: str, refresh_token: str):
    """로그인 정보를 로컬 파일에 저장"""
    try:
        data = {
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        _SESSION_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # 세션 저장 실패는 무시


def _load_session() -> dict | None:
    """저장된 세션 파일 로드"""
    try:
        if _SESSION_FILE.exists():
            return json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _clear_session_file():
    """세션 파일 삭제"""
    try:
        if _SESSION_FILE.exists():
            _SESSION_FILE.unlink()
    except Exception:
        pass


# ─── 자동 로그인 복원 ────────────────────────────────────────

def try_restore_session() -> bool:
    """저장된 세션으로 자동 로그인 시도. 성공 시 True."""
    if is_authenticated():
        return True

    saved = _load_session()
    if not saved:
        return False

    try:
        client = get_supabase_client()
        # refresh_token으로 세션 갱신
        res = client.auth.refresh_session(saved["refresh_token"])
        if res.session and res.user:
            st.session_state["user"] = res.user
            st.session_state["access_token"] = res.session.access_token
            # 갱신된 토큰으로 파일 업데이트
            _save_session(
                res.user.email,
                res.session.access_token,
                res.session.refresh_token,
            )
            return True
    except Exception:
        # 토큰 만료 또는 오류 → 세션 파일 삭제
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
    """현재 세션에서 로그인 여부 확인 및 사이드바 app 숨김 처리"""
    st.markdown('<style>[data-testid="stSidebarNavItems"] li:first-child { display: none !important; }</style>', unsafe_allow_html=True)
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
