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
import base64
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


def get_supabase_client() -> Client:
    """접속자(브라우저 세션)마다 따로 쓰는 Supabase 클라이언트.

    예전에는 st.cache_resource 로 모든 접속자가 클라이언트 하나를 같이 썼다.
    그러면 마지막에 로그인한 사람의 토큰으로 다른 사람의 조회·저장이 실행될 수 있다.
    """
    client = st.session_state.get("_sb_client")
    if client is None:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        if not url or not key:
            st.error("⚠️ Supabase 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
            st.stop()
        client = create_client(url, key, options=None)
        st.session_state["_sb_client"] = client
    return client


# ─── 세션 쿠키 & LocalStorage 저장/로드 ────────────────────────────────────

def _encode_cred(email: str, password: str) -> str:
    """이메일과 비밀번호를 단순 Base64로 난독화"""
    raw = f"{email}::{password}"
    return base64.b64encode(raw.encode('utf-8')).decode('utf-8')

def _decode_cred(encoded: str) -> tuple[str, str] | None:
    """난독화된 자격증명 복원"""
    try:
        raw = base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        email, pwd = raw.split("::", 1)
        return email, pwd
    except Exception:
        return None

def _save_session(encoded_cred: str) -> bool:
    """로그인 정보를 브라우저 쿠키와 LocalStorage에 이중 저장"""
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.set("sb_auto_login", encoded_cred, max_age=365*24*60*60)
    except Exception as e:
        print(f"Cookie save error: {e}")
        
    ls_done = False
    try:
        res = local_storage("set", storage_key="sb_auto_login", value=encoded_cred, component_key="ls_set_cred")
        if res == "set_done": ls_done = True
    except Exception as e:
        print(f"LocalStorage save error: {e}")
        
    return ls_done


def _load_session() -> str | None:
    """
    저장된 브라우저 쿠키/LocalStorage 로드
    반환값:
    - str: 난독화된 자격증명
    - "EMPTY": 응답을 받았으나 로그인 정보 없음
    - None: 아직 컴포넌트 응답 대기 중 (Loading)
    """
    try:
        ls_data = local_storage("get_all", component_key="ls_get_all")
        if ls_data is not None:
            # LocalStorage 응답 완료
            if isinstance(ls_data, dict):
                # 새로운 패스워드 방식
                auto_login = ls_data.get("auto_login")
                if auto_login:
                    return auto_login
                    
            # LocalStorage에 없으면 Cookie Fallback
            cookie_manager = get_cookie_manager()
            auto_login_cookie = cookie_manager.get("sb_auto_login")
            
            if auto_login_cookie:
                return auto_login_cookie
                
            return "EMPTY"
    except Exception as e:
        print(f"Session load error: {e}")
        
    return None


def _clear_session_file() -> bool:
    """세션 쿠키 및 LocalStorage 삭제"""
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.delete("sb_auto_login")
        cookie_manager.delete(_COOKIE_KEY_REFRESH)
        cookie_manager.delete(_COOKIE_KEY_EMAIL)
    except Exception as e:
        print(f"Cookie clear error: {e}")
        
    ls_done = False
    try:
        res = local_storage("remove", storage_key="sb_auto_login", component_key="ls_rem_cred")
        if res == "remove_done": ls_done = True
        
        # 이전 버전 찌꺼기 정리
        local_storage("remove", storage_key="sb_refresh_token", component_key="ls_rem_old_1")
        local_storage("remove", storage_key="sb_user_email", component_key="ls_rem_old_2")
    except Exception as e:
        print(f"LocalStorage clear error: {e}")
        
    return ls_done


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

    if isinstance(saved, str):
        decoded = _decode_cred(saved)
        if not decoded:
            _clear_session_file()
            return False
            
        email, password = decoded
        
        if "_bad_creds" not in st.session_state:
            st.session_state["_bad_creds"] = set()
            
        if saved in st.session_state["_bad_creds"]:
            _clear_session_file()
            return False

        try:
            client = get_supabase_client()
            # 패스워드로 완전한 새 세션 발급 (백그라운드 로그인)
            res = client.auth.sign_in_with_password({"email": email, "password": password})
            if res.session and res.user:
                st.session_state["user"] = res.user
                st.session_state["access_token"] = res.session.access_token
                st.session_state["_pending_session_save"] = saved
                _save_session(saved)
                return True
        except Exception:
            # 비밀번호 변경 등으로 인한 로그인 실패
            st.session_state["_bad_creds"].add(saved)
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
            
            encoded_cred = _encode_cred(email, password)
            
            # 즉시 저장하지 않고 플래그 세팅 (st.switch_page 등으로 컴포넌트가 무시되는 현상 방지)
            st.session_state["_pending_session_save"] = encoded_cred
            _save_session(encoded_cred)
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
    for key in ["user", "access_token", "_sb_client"]:
        st.session_state.pop(key, None)
    st.session_state["_pending_session_clear"] = True
    _clear_session_file()


def is_authenticated() -> bool:
    """현재 세션에서 로그인 여부 확인 (미뤄 둔 자동 로그인 저장·삭제도 처리)"""
    # ── 지연된 세션 저장 처리 ──
    if "_pending_session_save" in st.session_state:
        encoded_cred = st.session_state["_pending_session_save"]
        if _save_session(encoded_cred):
            del st.session_state["_pending_session_save"]
            
    if "_pending_session_clear" in st.session_state:
        if _clear_session_file():
            del st.session_state["_pending_session_clear"]
        
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
