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
        st.switch_page("0_🏠_홈.py")

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

# ── 월별 자산 목표 설정 ────────────────────────────────────
from utils.db import get_monthly_goals, upsert_monthly_goal
from datetime import datetime
import pandas as pd

st.subheader("🎯 월별 총 자산 목표 설정")
st.caption("대시보드에서 진척도를 추적하기 위한 연도별/월별 목표액을 입력하세요.")

target_year = st.selectbox("연도 선택", list(range(2024, 2030)), index=list(range(2024, 2030)).index(datetime.now().year))

# DB에서 가져오기
goals_data = get_monthly_goals(target_year)
goals_dict = {g["month"]: g.get("target_amount", 0) for g in goals_data}

# 데이터 프레임 준비 (1월~12월)
df_data = []
for m in range(1, 13):
    df_data.append({
        "월": f"{m}월",
        "목표 현금성 자산 (원)": goals_dict.get(m, 0)
    })

edited_df = st.data_editor(
    pd.DataFrame(df_data),
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "월": st.column_config.TextColumn("월", disabled=True),
        "목표 현금성 자산 (원)": st.column_config.NumberColumn("목표 현금성 자산 (원)", min_value=0, format="%d", step=10000)
    },
    key=f"goals_editor_{target_year}"
)

if st.button("목표 저장", type="secondary", use_container_width=True):
    success_count = 0
    for idx, row in edited_df.iterrows():
        month = idx + 1
        val = row["목표 현금성 자산 (원)"]
        target_amt = 0 if pd.isna(val) else int(val)
        if upsert_monthly_goal(target_year, month, target_amt):
            success_count += 1
    
    if success_count == 12:
        st.success(f"✅ {target_year}년도 월별 목표가 성공적으로 저장되었습니다.")
    else:
        st.warning(f"⚠️ 일부 데이터 저장에 실패했습니다. ({success_count}/12)")

st.divider()

# ── 로그아웃 ────────────────────────────────────────────────
st.subheader("🚪 로그아웃")
if st.button("로그아웃", type="primary"):
    logout()
    st.success("로그아웃 되었습니다.")
    st.switch_page("0_🏠_홈.py")
