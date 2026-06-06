"""
pages/1_📊_대시보드.py  ─  자산 현황 메인 대시보드
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="대시보드 | Asset Tracker", page_icon="📊", layout="wide")

from utils.auth import is_authenticated, get_current_user, try_restore_session, EMAIL_TO_NAME
from utils.db import get_monthly_summary, get_transactions

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("app.py")

now = datetime.now()

# ── 헤더 ─────────────────────────────────────────────────
st.title("📊 자산 현황 대시보드")
user = get_current_user()
_email = user.email if user else ""
_name  = EMAIL_TO_NAME.get(_email, _email)
st.caption(f"👤 {_name} ({_email})")

# ── 월 선택 ──────────────────────────────────────────────
col_y, col_m, _ = st.columns([1, 1, 5])
with col_y:
    year = st.selectbox("연도", [2025, 2026, 2027], index=1, key="dash_year")
with col_m:
    month = st.selectbox("월", list(range(1, 13)), index=now.month - 1, key="dash_month")

st.divider()

# ── 데이터 로드 ───────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    s = get_monthly_summary(year, month)

ti  = s["total_income"]
tf  = s["total_fixed"]
tv  = s["total_variable"]
tu  = s["total_utility"]
te  = s["total_expense"]
net = s["net"]
cat = s["category_totals"]
tinv = s["total_investment"]

# ── KPI 카드 ─────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💰 총 수입",   f"₩{ti:,.0f}")
c2.metric("🔒 고정비",    f"₩{tf:,.0f}")
c3.metric("🛒 변동비",    f"₩{tv + tu:,.0f}")
c4.metric("💵 잔여금",    f"₩{net:,.0f}",
          delta="흑자 ▲" if net >= 0 else "적자 ▼",
          delta_color="normal" if net >= 0 else "inverse")
c5.metric("📈 투자 자산", f"₩{tinv:,.0f}")

st.divider()

# ── 차트 ─────────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    st.subheader("📊 수입 vs 지출 구조")
    if ti > 0 or te > 0:
        fig = go.Figure(data=[
            go.Bar(name="수입",   x=[f"{year}년 {month}월"], y=[ti],
                   marker_color="#60a5fa"),
            go.Bar(name="고정비", x=[f"{year}년 {month}월"], y=[tf],
                   marker_color="#f87171"),
            go.Bar(name="공과금", x=[f"{year}년 {month}월"], y=[tu],
                   marker_color="#fb923c"),
            go.Bar(name="변동비", x=[f"{year}년 {month}월"], y=[tv],
                   marker_color="#a78bfa"),
        ])
        fig.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.1)",
                         tickformat=",.0f", tickprefix="₩")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📌 데이터가 없습니다. 가계부 메뉴에서 입력하세요.")

with col_r:
    st.subheader("🍰 변동지출 구성")
    if cat:
        fig2 = px.pie(
            values=list(cat.values()),
            names=list(cat.keys()),
            color_discrete_sequence=["#a78bfa","#60a5fa","#34d399","#fb923c",
                                      "#f87171","#fbbf24","#e879f9"],
            hole=0.45,
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            height=300, margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(font=dict(size=11)),
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📌 변동지출 데이터가 없습니다.")

st.divider()

# ── 수입 상세 ─────────────────────────────────────────────
st.subheader("💼 수입 상세")
inc = s["income_detail"]
if inc:
    di = pd.DataFrame([
        {"구분": "준영 정기급여", "금액": inc.get("junyoung_salary", 0)},
        {"구분": "준영 상여금",   "금액": inc.get("junyoung_bonus", 0)},
        {"구분": "지윤 정기급여", "금액": inc.get("jiyun_salary", 0)},
        {"구분": "지윤 인센티브", "금액": inc.get("jiyun_incentive", 0)},
    ])
    di["금액"] = di["금액"].apply(lambda x: f"₩{x:,}")
    st.dataframe(di, use_container_width=True, hide_index=True)
else:
    st.info("📌 수입 데이터가 없습니다. 가계부 → 수입 탭에서 입력하세요.")

st.divider()

# ── 최근 변동지출 내역 ────────────────────────────────────
st.subheader(f"🧾 {year}년 {month}월 변동지출 내역")
txns = get_transactions(year, month)
if txns:
    df = pd.DataFrame(txns)[["day", "category", "description", "amount"]]
    df.columns = ["일", "구분", "이용처", "금액(원)"]
    df["금액(원)"] = df["금액(원)"].apply(lambda x: f"₩{x:,}")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"총 {len(txns)}건 / 합계 ₩{tv:,}")
else:
    st.info("📌 변동지출 내역이 없습니다. 가계부 메뉴에서 입력하세요.")
