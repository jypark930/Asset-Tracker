"""
app_pages/settings.py  ─  계정 정보, 월별 목표, 로그아웃
"""
import os

import pandas as pd
import streamlit as st

from utils.auth import get_current_user, logout, EMAIL_TO_NAME
from utils.db import get_monthly_goals, upsert_monthly_goal
from utils.ui import page_header, now_kst, flash

page_header("설정", show_month=False)

user = get_current_user()
_email = user.email if user else ""
_name = EMAIL_TO_NAME.get(_email, _email)

# ── 계정 ────────────────────────────────────────────────
with st.container(border=True, key="glass_settings_1"):
    st.markdown("#### :material/person: 계정")
    c1, c2 = st.columns(2)
    c1.text_input("이름", value=_name, disabled=True)
    c2.text_input("이메일", value=_email, disabled=True)

    supabase_url = os.getenv("SUPABASE_URL", "")
    if supabase_url and "your-project" not in supabase_url:
        st.caption(f":material/cloud_done: 연결됨: {supabase_url}")
    else:
        st.error("Supabase 주소가 설정되지 않았습니다. .env 파일을 확인하세요.")

    if st.button("로그아웃", icon=":material/logout:"):
        logout()
        st.rerun()

# ── 월별 목표 ────────────────────────────────────────────
with st.container(border=True, key="glass_settings_2"):
    st.markdown("#### :material/flag: 월별 현금성 자산 목표")
    st.caption("대시보드의 목표 달성률에 쓰입니다. 목표는 계정마다 따로 저장됩니다.")

    this_year = now_kst().year
    years = list(range(2024, this_year + 4))
    target_year = st.segmented_control("연도", years, default=this_year, key="goal_year")
    if target_year is None:
        target_year = this_year

    goals_data = get_monthly_goals(target_year)
    goals_dict = {g["month"]: g.get("target_amount", 0) or 0 for g in goals_data}

    df = pd.DataFrame({
        "월": [f"{m}월" for m in range(1, 13)],
        "목표 (원)": [int(goals_dict.get(m, 0)) for m in range(1, 13)],
    })

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        hide_index=True,
        column_config={
            "월": st.column_config.TextColumn("월", disabled=True, width="small"),
            "목표 (원)": st.column_config.NumberColumn("목표 (원)", min_value=0, format="localized", step=10000),
        },
        key=f"goals_editor_{target_year}", height=40 + 35 * len(df),
    )

    def _to_int(v) -> int:
        return 0 if v is None or pd.isna(v) else int(v)

    changed = [
        (i + 1, _to_int(row["목표 (원)"]))
        for i, row in edited_df.iterrows()
        if _to_int(row["목표 (원)"]) != int(goals_dict.get(i + 1, 0))
    ]
    if changed:
        st.caption(f"바뀐 달: {', '.join(f'{m}월' for m, _ in changed)}")

    if st.button("목표 저장", type="primary", icon=":material/save:", disabled=not changed):
        ok = sum(upsert_monthly_goal(target_year, m, v) for m, v in changed)
        if ok == len(changed):
            flash(f"{target_year}년 목표 {ok}개 달을 저장했습니다.")
            st.rerun()
        else:
            st.warning(f"일부 저장에 실패했습니다. ({ok}/{len(changed)})")
