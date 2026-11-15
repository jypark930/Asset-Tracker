"""
0_🏠_홈.py  ─  Asset Tracker 진입점
로그인 여부에 따라 보여 줄 페이지 목록을 정하고, 공통 스타일을 한 번만 넣는다.
(Streamlit Cloud 의 메인 파일 이름이라 파일 이름은 바꾸지 않는다)
"""
import streamlit as st

st.set_page_config(
    page_title="Asset Tracker",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
)

from utils.auth import is_authenticated, try_restore_session
from utils.ui import inject_global_css

inject_global_css()

logged_in = is_authenticated() or try_restore_session()

if not logged_in:
    pg = st.navigation([st.Page("app_pages/login.py", title="로그인", icon=":material/login:")],
                       position="hidden")
else:
    pg = st.navigation(
        [
            st.Page("app_pages/ledger.py", title="가계부", icon=":material/receipt_long:",
                    url_path="ledger", default=True),
            st.Page("app_pages/dashboard.py", title="대시보드", icon=":material/space_dashboard:",
                    url_path="dashboard"),
            st.Page("app_pages/finance.py", title="재무현황", icon=":material/account_balance:",
                    url_path="finance"),
            st.Page("app_pages/invest.py", title="투자현황", icon=":material/trending_up:",
                    url_path="invest"),
            st.Page("app_pages/ai.py", title="AI 점검", icon=":material/smart_toy:",
                    url_path="ai"),
            st.Page("app_pages/settings.py", title="설정", icon=":material/settings:",
                    url_path="settings"),
        ],
        position="top",
    )

st.session_state.pop("_tip_slot", None)   # 지난번에 중간에 멈춘 화면의 자리는 버린다
pg.run()

if logged_in:
    from utils import tips
    tips.fill()                           # 화면을 다 그린 뒤 맨 위 한 줄 조언을 AI 문장으로 바꾼다
