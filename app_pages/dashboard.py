"""
app_pages/dashboard.py  ─  한 달 요약 + 자산 목표 + 추이
"""
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from utils.db import (
    INVESTMENT_ACCOUNTS, TREND_CATEGORIES,
    get_monthly_summary, get_all_cash_assets, get_all_household_trends,
)
from utils.ui import (
    page_header, prev_of, won, won_short, kpi_card, kpi_grid, delta_text,
)

year, month = page_header("대시보드")
py, pm = prev_of(year, month)

with st.spinner("불러오는 중..."):
    s = get_monthly_summary(year, month)
    ps = get_monthly_summary(py, pm)

CASH_ACCOUNTS = INVESTMENT_ACCOUNTS.get("현금성 자산", [])


def _cash(summary: dict) -> int:
    return sum((i.get("principal") or 0) for i in summary.get("investments", [])
               if i.get("account_type") in CASH_ACCOUNTS)


# ── 이번 달 돈의 흐름 ──────────────────────────────────────
st.markdown("#### :material/payments: 이번 달 돈의 흐름")

has_any = s["total_income"] or s["total_expense"]
if not has_any:
    st.caption(f"{year}년 {month}월에는 아직 입력된 수입·지출이 없습니다.")

net_d, net_c = delta_text(s["net"], ps["net"], more_is_bad=False)
exp_d, exp_c = delta_text(s["total_expense"], ps["total_expense"])
inc_d, inc_c = delta_text(s["total_income"], ps["total_income"], more_is_bad=False)
var_d, var_c = delta_text(s["total_variable"], ps["total_variable"])
fix_d, fix_c = delta_text(s["total_fixed"], ps["total_fixed"])
utl_d, utl_c = delta_text(s["total_utility"], ps["total_utility"])

kpi_grid([
    kpi_card("총 수입", won(s["total_income"]), inc_d, inc_c),
    kpi_card("총 지출", won(s["total_expense"]), exp_d, exp_c),
    kpi_card("남은 돈 (수입-지출)", won(s["net"]),
             ("흑자 · " if s["net"] >= 0 else "적자 · ") + net_d, net_c, highlight=True),
    kpi_card("고정비", won(s["total_fixed"]), fix_d, fix_c),
    kpi_card("변동지출", won(s["total_variable"]), var_d, var_c),
    kpi_card("공과금", won(s["total_utility"]), utl_d, utl_c),
])

# ── 자산 ─────────────────────────────────────────────────
st.markdown("#### :material/savings: 자산")

cash_now, cash_prev = _cash(s), _cash(ps)
total_now, total_prev = s.get("total_principal") or 0, ps.get("total_principal") or 0
cd, cc = delta_text(cash_now, cash_prev, more_is_bad=False)
td, tc = delta_text(total_now, total_prev, more_is_bad=False)

all_cash = get_all_cash_assets(start_year=2026, start_month=5)
curr_goal = next((a for a in all_cash if (a["year"], a["month"]) == (year, month)), None)
target = (curr_goal or {}).get("target") or 0

goal_html = ""
if target:
    rate = cash_now / target * 100 if target else 0
    ev = (curr_goal or {}).get("raw_evaluation") or 0
    gap = cash_now - target
    gap_txt = f"목표보다 {won_short(abs(gap))} {'많음' if gap >= 0 else '부족'}"
    goal_html = f"""
<div class='at-goal'>
  <div class='row'><span>이번 달 현금성 자산 목표</span><span>{won(target)}</span></div>
  <div class='bar'><div style='width:{min(rate, 100):.1f}%'></div></div>
  <div class='row'><span>원금 {won(cash_now)} · <b>{rate:.1f}%</b></span>
       <span style='color:{"#16a34a" if gap >= 0 else "#dc2626"}'>{gap_txt}</span></div>
  <div class='row' style='color:#94a3b8;font-size:0.78rem'><span>평가금 {won(ev)}</span><span></span></div>
</div>"""

kpi_grid([
    kpi_card("현금성 자산 (원금)", won(cash_now), cd, cc),
    kpi_card("총 자산 (원금)", won(total_now), td, tc),
    kpi_card("목표 달성률", f"{cash_now / target * 100:.1f}%" if target else "목표 없음",
             "설정에서 목표를 넣을 수 있어요" if not target else f"목표 {won_short(target)}"),
])
if goal_html:
    st.markdown(goal_html, unsafe_allow_html=True)


# ── 현금성 자산 추이 ─────────────────────────────────────
def _line_layout(fig, height=300, unit=""):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="KoPub, sans-serif", color="#475569"),
        xaxis=dict(showgrid=False, tickformat="%y.%m", dtick="M1", fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor="#eef2f6", tickformat=",.0f", fixedrange=True,
                   title=dict(text=unit, font=dict(size=11, color="#94a3b8"))),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=8, r=8, t=30, b=8), height=height, hovermode="x unified",
    )


with st.container(border=True):
    st.markdown("**현금성 자산 추이** · 마감한 달까지")
    dates = [datetime(a["year"], a["month"], 1) for a in all_cash]

    def _m(v):
        return v / 1_000_000 if v else None

    fig = go.Figure()
    fig.add_scatter(x=dates, y=[_m(a["target"]) for a in all_cash], name="목표", mode="lines",
                    line=dict(color="#cbd5e1", width=2, dash="dash"),
                    hovertemplate="%{y:,.1f}백만<extra>목표</extra>", connectgaps=True)
    fig.add_scatter(x=dates, y=[_m(a["principal"]) for a in all_cash], name="원금", mode="lines+markers",
                    line=dict(color="#3b82f6", width=3),
                    hovertemplate="%{y:,.1f}백만<extra>원금</extra>", connectgaps=True)
    fig.add_scatter(x=dates, y=[_m(a["evaluation"]) for a in all_cash], name="평가금", mode="lines+markers",
                    line=dict(color="#10b981", width=3),
                    hovertemplate="%{y:,.1f}백만<extra>평가금</extra>", connectgaps=True)
    _line_layout(fig, unit="백만원")
    if any(_m(a[k]) for a in all_cash for k in ("target", "principal", "evaluation")):
        st.plotly_chart(fig, config={"displayModeBar": False})
    else:
        st.caption("표시할 값이 없습니다. 투자현황에서 달을 마감하거나 설정에서 목표를 넣으면 그래프가 나옵니다.")


# ── 변동지출 카테고리 ─────────────────────────────────────
st.markdown("#### :material/category: 변동지출 카테고리")
cat_now = s["category_totals"]
cat_prev = ps["category_totals"]
items = sorted([(c, v) for c, v in cat_now.items() if v], key=lambda x: -x[1])

if not items:
    st.caption("이번 달 변동지출이 없습니다. 가계부에서 입력하세요.")
else:
    top = items[0][1] or 1
    rows = ""
    for c, v in items:
        p = cat_prev.get(c, 0)
        d = v - p
        if d > 0:
            dcls, dtxt = "up", f"▲ {won_short(d)}"
        elif d < 0:
            dcls, dtxt = "down", f"▼ {won_short(-d)}"
        else:
            dcls, dtxt = "same", "변동 없음"
        rows += (f"<div class='at-cat'><div class='name'>{c}</div>"
                 f"<div class='track'><div style='width:{v / top * 100:.1f}%'></div></div>"
                 f"<div class='amt'>{won(v)}<span class='d {dcls}'>{dtxt}</span></div></div>")
    with st.container(border=True):
        st.markdown(rows, unsafe_allow_html=True)
        st.caption(f"합계 {won(s['total_variable'])} · 전월 대비 금액은 오른쪽 아래 작은 글씨")


# ── 월별 추이 ────────────────────────────────────────────
st.markdown("#### :material/show_chart: 월별 추이")
with st.container(border=True):
    QUICK = ["총 지출", "변동비 총액", "총 수입", "잔여금(수입-지출)"]
    pick = st.segmented_control("항목", QUICK, default="총 지출", key="trend_quick",
                                label_visibility="collapsed")
    with st.expander("다른 항목 보기", icon=":material/tune:"):
        other = st.selectbox("항목 선택", ["(위에서 고른 항목)"] + [c for c in TREND_CATEGORIES if c not in QUICK],
                             key="trend_other")
    selected = other if other and other != "(위에서 고른 항목)" else (pick or "총 지출")

    trend = get_all_household_trends(start_year=2026, start_month=5)
    tdates = [datetime(t["year"], t["month"], 1) for t in trend]
    tvals = [t["values"].get(selected) for t in trend]

    fig2 = go.Figure()
    fig2.add_scatter(x=tdates, y=tvals, mode="lines+markers", name=selected,
                     line=dict(color="#ff6b00", width=3), marker=dict(size=7),
                     fill="tozeroy", fillcolor="rgba(255,107,0,0.08)",
                     hovertemplate="₩%{y:,.0f}<extra></extra>", connectgaps=True)
    _line_layout(fig2, unit="원")
    fig2.update_layout(showlegend=False, margin=dict(l=8, r=8, t=10, b=8))
    st.caption(selected)
    st.plotly_chart(fig2, config={"displayModeBar": False})
