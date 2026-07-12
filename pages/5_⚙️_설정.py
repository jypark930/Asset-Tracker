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
        target_amt = int(row["목표 현금성 자산 (원)"] or 0)
        if upsert_monthly_goal(target_year, month, target_amt):
            success_count += 1
    
    if success_count == 12:
        st.success(f"✅ {target_year}년도 월별 목표가 성공적으로 저장되었습니다.")
    else:
        st.warning(f"⚠️ 일부 데이터 저장에 실패했습니다. ({success_count}/12)")

st.divider()

# ── 임시: 목표 일괄 등록 ─────────────────────────────────────
st.subheader("🛠️ 임시: 목표 일괄 등록")
st.caption("요청하신 26년 5월 ~ 28년 12월 목표를 일괄 등록합니다.")
if st.button("목표 일괄 등록 실행", type="primary", use_container_width=True):
    raw_data = """26년 5월	 175,164,863 
26년 6월	 179,857,899 
26년 7월	 183,862,636 
26년 8월	 187,867,372 
26년 9월	 191,872,109 
26년 10월	 195,876,846 
26년 11월	 199,881,583 
26년 12월	 203,886,319 
27년 1월	 207,891,056 
27년 2월	 211,895,793 
27년 3월	 215,900,529 
27년 4월	 219,905,266 
27년 5월	 223,910,003 
27년 6월	 227,914,739 
27년 7월	 231,919,476 
27년 8월	 235,924,213 
27년 9월	 239,928,950 
27년 10월	 243,933,686 
27년 11월	 247,938,423 
27년 12월	 251,943,160 
28년 1월	 255,947,896 
28년 2월	 259,952,633 
28년 3월	 263,957,370 
28년 4월	 267,962,106 
28년 5월	 271,966,843 
28년 6월	 275,971,580 
28년 7월	 279,976,317 
28년 8월	 283,981,053 
28년 9월	 287,985,790 
28년 10월	 291,990,527 
28년 11월	 295,995,263 
28년 12월	 300,000,000"""
    
    with st.spinner("일괄 등록 중..."):
        success = 0
        for line in raw_data.split("\n"):
            parts = line.strip().split("\t")
            if len(parts) == 2:
                date_parts = parts[0].strip().split(" ")
                year = int(date_parts[0].replace("년", "")) + 2000
                month = int(date_parts[1].replace("월", ""))
                amt = int(parts[1].strip().replace(",", ""))
                
                if upsert_monthly_goal(year, month, amt):
                    success += 1
        st.success(f"✅ 총 {success}개의 월별 목표 데이터가 성공적으로 등록되었습니다! (새로고침하여 대시보드에서 확인하세요)")

st.divider()

# ── 로그아웃 ────────────────────────────────────────────────
st.subheader("🚪 로그아웃")
if st.button("로그아웃", type="primary"):
    logout()
    st.success("로그아웃 되었습니다.")
    st.switch_page("0_🏠_홈.py")
