"""
app_pages/dashboard.py  ─  한 달을 한 장으로: 확인할 일 → 돈의 흐름 → 자산·목표 → 지출 구성 → 추이
"""
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from utils.db import (
    INVESTMENT_ACCOUNTS, TREND_CATEGORIES,
    get_monthly_summary, get_all_cash_assets, get_all_household_trends,
)
from utils.fin import confirmed_fields, unconfirmed_count
from utils.ui import (
    page_header, prev_of, now_kst, won, won_short, kpi_card, kpi_grid, delta_text, ring_gauge,
    roll_number, flow_bar, legend_item,
)

year, month = page_header("대시보드")
py, pm = prev_of(year, month)
now = now_kst()

with st.spinner("불러오는 중..."):
    s = get_monthly_summary(year, month)
    ps = get_monthly_summary(py, pm)

CASH_ACCOUNTS = INVESTMENT_ACCOUNTS.get("현금성 자산", [])
C_FIXED, C_UTIL, C_VAR, C_LEFT = "#60a5fa", "#a78bfa", "#f472b6", "#34d399"


def _cash(summary: dict) -> int:
    return sum((i.get("principal") or 0) for i in summary.get("investments", [])
               if i.get("account_type") in CASH_ACCOUNTS)


# ── 확인할 일 ────────────────────────────────────────────
todos = []
if (year, month) <= (now.year, now.month):
    n_unc = unconfirmed_count(s["income_detail"], s["fixed_detail"], s["utility_detail"])
    if n_unc:
        todos.append((f"재무현황에 아직 '예상' 값인 항목이 {n_unc}개 있어요. 금액이 맞으면 확정해 주세요.",
                      "app_pages/finance.py", "재무현황 열기"))
if (year, month) == (now.year, now.month) and ps["investments"] \
        and "investments_closed" not in confirmed_fields(ps["income_detail"]):
    todos.append((f"지난달({pm}월) 투자현황을 아직 마감하지 않았어요.", "app_pages/invest.py", "투자현황 열기"))

for msg, page, label in todos:
    c1, c2 = st.columns([5, 1.3], vertical_alignment="center")
    c1.markdown(f"<div class='at-todo'>{msg}</div>", unsafe_allow_html=True)
    c2.page_link(page, label=label, icon=":material/arrow_forward:")

# ── 돈의 흐름 + 자산·목표 ─────────────────────────────────
left, right = st.columns([3, 2], gap="medium")

with left:
    inc, fixed, util, var = s["total_income"], s["total_fixed"], s["total_utility"], s["total_variable"]
    net = s["net"]
    nd, nc = delta_text(net, ps["net"], more_is_bad=False)
    sign_txt = "흑자" if net >= 0 else "적자"
    color = "var(--at-green)" if net >= 0 else "var(--at-red)"
    if not (inc or s["total_expense"]):
        body = f"<div class='sub'>{year}년 {month}월에는 아직 입력된 수입·지출이 없습니다.</div>"
    else:
        def _pct(v):
            return f"수입의 {v / inc * 100:.0f}%" if inc else ""

        fd, fc = delta_text(fixed, ps["total_fixed"])
        ud, uc = delta_text(util, ps["total_utility"])
        vd, vc = delta_text(var, ps["total_variable"])
        id_, ic = delta_text(inc, ps["total_income"], more_is_bad=False)
        body = (
            flow_bar([("고정비", fixed, C_FIXED), ("공과금", util, C_UTIL), ("변동지출", var, C_VAR),
                      ("남은 돈", max(net, 0), C_LEFT)], inc)
            + "<div class='at-legend'>"
            + legend_item("수입", won(inc), "rgba(255,255,255,0.5)", id_, ic)
            + legend_item("고정비", won(fixed), C_FIXED, fd, fc, _pct(fixed))
            + legend_item("공과금", won(util), C_UTIL, ud, uc)
            + legend_item("변동지출", won(var), C_VAR, vd, vc, _pct(var))
            + "</div>"
        )
    st.markdown(
        "<div class='at-kpi at-hero'>"
        f"<div class='lbl'>{month}월 남은 돈 (수입 − 지출)</div>"
        f"<div class='big' style='color:{color}'>{roll_number(won(net))}</div>"
        f"<div class='sub'>{sign_txt} · {nd}</div>{body}</div>",
        unsafe_allow_html=True,
    )

all_cash = get_all_cash_assets(start_year=2026, start_month=5)
cash_now, cash_prev = _cash(s), _cash(ps)
total_now, total_prev = s.get("total_principal") or 0, ps.get("total_principal") or 0

with right:
    curr_goal = next((a for a in all_cash if (a["year"], a["month"]) == (year, month)), None)
    target = (curr_goal or {}).get("target") or 0
    if target:
        rate = cash_now / target * 100
        gap = cash_now - target
        gap_color = "#34d399" if gap >= 0 else "#f87171"
        st.markdown(
            "<div class='at-ring-card'>" + ring_gauge(rate, "현금성 목표") +
            "<div class='at-ring-info'>"
            f"<div class='row'><span>목표</span><b>{won_short(target)}</b></div>"
            f"<div class='row'><span>현재 원금</span><b>{won_short(cash_now)}</b></div>"
            f"<div class='row'><span>{'남음' if gap >= 0 else '부족'}</span>"
            f"<b style='color:{gap_color}'>{won_short(abs(gap))}</b></div>"
            "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        with st.container(border=True, key="glass_dash_goal"):
            st.markdown("**현금성 자산 목표가 없어요**")
            st.caption("목표를 넣으면 달성률을 원형 게이지로 보여 줘요.")
            st.page_link("app_pages/settings.py", label="설정에서 목표 넣기", icon=":material/flag:")
    cd, cc = delta_text(cash_now, cash_prev, more_is_bad=False)
    td, tc = delta_text(total_now, total_prev, more_is_bad=False)
    st.markdown(
        "<div class='at-grid' style='grid-template-columns:1fr 1fr'>"
        + kpi_card("현금성 자산", won_short(cash_now), cd.replace("전월 대비 ", ""), cc)
        + kpi_card("총 자산 (원금)", won_short(total_now), td.replace("전월 대비 ", ""), tc)
        + "</div>",
        unsafe_allow_html=True,
    )


# ── 그래프 공통 모양 ──────────────────────────────────────
def _line_layout(fig, height=300, unit=""):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="KoPub, sans-serif", color="#9ca3af"),
        xaxis=dict(showgrid=False, tickformat="%y.%m", nticks=8, tickangle=0, fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickformat=",.0f", fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#2a292e", bordercolor="rgba(255,255,255,0.15)", font=dict(color="#f3f4f6")),
        margin=dict(l=8, r=8, t=30, b=8), height=height, hovermode="x unified",
    )


# ── 현금성 자산 추이 ─────────────────────────────────────
with st.container(border=True, key="glass_1"):
    st.markdown("**:material/savings: 현금성 자산 추이** · 마감한 달까지 · 단위 백만원")
    # 가로축은 마감한 마지막 달까지만 (원금이 None 이면 마감 뒤 달). 목표가 먼 미래까지 있어도 자른다.
    chart_cash = [a for a in all_cash if a["principal"] is not None]
    dates = [datetime(a["year"], a["month"], 1) for a in chart_cash]

    def _m(v):
        return v / 1_000_000 if v else None

    fig = go.Figure()
    fig.add_scatter(x=dates, y=[_m(a["target"]) for a in chart_cash], name="목표", mode="lines",
                    line=dict(color="rgba(255,255,255,0.35)", width=2, dash="dash"),
                    hovertemplate="%{y:,.1f}백만<extra>목표</extra>", connectgaps=True)
    fig.add_scatter(x=dates, y=[_m(a["principal"]) for a in chart_cash], name="원금", mode="lines+markers",
                    line=dict(color="#60a5fa", width=3, shape="spline"),
                    hovertemplate="%{y:,.1f}백만<extra>원금</extra>", connectgaps=True)
    fig.add_scatter(x=dates, y=[_m(a["evaluation"]) for a in chart_cash], name="평가금", mode="lines+markers",
                    line=dict(color="#34d399", width=3, shape="spline"),
                    hovertemplate="%{y:,.1f}백만<extra>평가금</extra>", connectgaps=True)
    _line_layout(fig, height=280, unit="백만원")
    if len(dates) <= 12:
        fig.update_xaxes(dtick="M1")  # 달이 적으면 한 달씩 눈금
    _vals = [v for a in chart_cash for k in ("target", "principal", "evaluation") if (v := _m(a[k]))]
    fig.update_yaxes(tickformat=",.0f" if _vals and max(_vals) >= 10 else ",.1f")
    if _vals:
        st.plotly_chart(fig, config={"displayModeBar": False})
    else:
        st.caption("마감한 달이 없어요. 투자현황에서 달을 마감하면 그래프가 나와요.")

# ── 변동지출 구성 | 월별 추이 ─────────────────────────────
c_left, c_right = st.columns(2, gap="medium")

with c_left, st.container(border=True, key="glass_2", height="stretch"):
    st.markdown(f"**:material/category: {month}월 변동지출** · {won(s['total_variable'])}")
    cat_now, cat_prev = s["category_totals"], ps["category_totals"]
    items = sorted([(c, v) for c, v in cat_now.items() if v], key=lambda x: -x[1])
    if not items:
        st.caption("이번 달 변동지출이 없습니다. 가계부에서 입력하세요.")
    else:
        top = items[0][1] or 1
        rows = ""
        for c, v in items:
            d = v - cat_prev.get(c, 0)
            dcls, dtxt = ("up", f"▲ {won_short(d)}") if d > 0 else ("down", f"▼ {won_short(-d)}") if d < 0 \
                else ("same", "변동 없음")
            rows += (f"<div class='at-cat'><div class='name'>{c}</div>"
                     f"<div class='track'><div style='width:{v / top * 100:.1f}%'></div></div>"
                     f"<div class='amt'>{won(v)}<span class='d {dcls}'>{dtxt}</span></div></div>")
        st.markdown(rows, unsafe_allow_html=True)
        st.caption("작은 글씨는 전월 대비")

with c_right, st.container(border=True, key="glass_3", height="stretch"):
    st.markdown("**:material/show_chart: 월별 추이**")
    QUICK = ["총 지출", "변동비 총액", "총 수입", "잔여금(수입-지출)"]
    pick = st.segmented_control("항목", QUICK, default="총 지출", key="trend_quick",
                                label_visibility="collapsed")
    with st.expander("다른 항목 보기", icon=":material/tune:"):
        other = st.selectbox("항목 선택", ["(위에서 고른 항목)"] + [c for c in TREND_CATEGORIES if c not in QUICK],
                             key="trend_other")
    selected = other if other and other != "(위에서 고른 항목)" else (pick or "총 지출")

    trend = get_all_household_trends(start_year=2026, start_month=5)
    fig2 = go.Figure()
    fig2.add_scatter(x=[datetime(t["year"], t["month"], 1) for t in trend],
                     y=[t["values"].get(selected) for t in trend],
                     mode="lines+markers", name=selected,
                     line=dict(color="#60a5fa", width=3, shape="spline"), marker=dict(size=7),
                     fill="tozeroy", fillcolor="rgba(59,130,246,0.14)",
                     hovertemplate="₩%{y:,.0f}<extra></extra>", connectgaps=True)
    _line_layout(fig2, height=260, unit="원")
    fig2.update_layout(showlegend=False, margin=dict(l=8, r=8, t=10, b=8))
    st.caption(f"{selected} · 단위 원")
    st.plotly_chart(fig2, config={"displayModeBar": False})
