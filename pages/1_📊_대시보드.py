"""
pages/1_📊_대시보드.py  ─  자산 현황 메인 대시보드
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="대시보드", page_icon="📊", layout="wide")

from utils.auth import is_authenticated, get_current_user, try_restore_session, EMAIL_TO_NAME
from utils.db import get_monthly_summary, get_transactions, get_monthly_goal, INVESTMENT_ACCOUNTS, get_yearly_cash_assets, get_all_cash_assets

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("0_🏠_홈.py")

now = datetime.now()


# ── 헬퍼 함수 ─────────────────────────────────────────────

def _get_card_html(title: str, value: str, delta: str = "", border_color: str = "#ff6b00", delta_color: str = "#10b981", is_highlight: bool = False):
    """라이트 테마 카드 HTML 문자열을 반환합니다."""
    delta_html = f"<div style='font-size: clamp(0.65rem, 2.5vw, 0.8rem);font-weight:600;color:{delta_color};margin-top:4px;white-space:nowrap;'>{delta}</div>" if delta else "<div style='font-size: clamp(0.65rem, 2.5vw, 0.8rem);font-weight:600;margin-top:4px;white-space:nowrap;visibility:hidden;'>&nbsp;</div>"

    if is_highlight:
        bg_style = "background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%); border: 2px solid #a855f7; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.25);"
        title_color = "#6b21a8"
        value_color = "#4c1d95"
    else:
        bg_style = "background: #ffffff; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.03);"
        title_color = "#64748b"
        value_color = "#1e293b"

    return f"""<div style="{bg_style} border-radius: 12px; padding: clamp(10px, 2.5vw, 20px) clamp(4px, 1.5vw, 14px); height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; overflow: hidden; transition: all 0.3s ease;">
<div style="width: 24px; height: 3px; background-color: {border_color}; border-radius: 2px; margin-bottom: clamp(6px, 2vw, 12px);"></div>
<div style="font-size: clamp(0.65rem, 2.5vw, 0.8rem);color:{title_color};font-weight:700;letter-spacing:0.02em;margin-bottom:6px;white-space:nowrap;">{title}</div>
<div style="font-size: clamp(0.85rem, 3.5vw, 1.35rem);font-weight:800;color:{value_color};font-family:'KoPubWorldBold', -apple-system, BlinkMacSystemFont, sans-serif;line-height:1.2;letter-spacing:-0.5px;white-space:nowrap;">{value}</div>
{delta_html}
</div>"""

def draw_neon_divider():
    st.markdown("""
    <hr style="height:1px;border:none;background:#e2e8f0;margin:16px 0;">
    """, unsafe_allow_html=True)


# ── 헤더 ─────────────────────────────────────────────────
user = get_current_user()

# ── 커스텀 네온 타이틀 ─────────────────────────
st.markdown("""
<div style="width: 100%; display: flex; justify-content: center; margin-bottom: 4px; margin-top: 10px;">
    <h1 style="font-size: 1.8rem; font-weight: 800; color: #1e293b; margin: 0 auto; text-align: center !important; width: 100%;">
        자산 현황 대시보드
    </h1>
</div>
""", unsafe_allow_html=True)

import plotly.graph_objects as go

# ── 현금성 자산 추이 (월별 선 그래프) ──────────────────────────
if "global_year" not in st.session_state:
    st.session_state.global_year = now.year

all_cash_assets = get_all_cash_assets(start_year=2026, start_month=5)
months_dates = [datetime(item["year"], item["month"], 1) for item in all_cash_assets]
targets = [item["target"] / 1_000_000 for item in all_cash_assets]
principals = [item["principal"] / 1_000_000 for item in all_cash_assets]
evaluations = [item["evaluation"] / 1_000_000 for item in all_cash_assets]

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(x=months_dates, y=targets, mode='lines+markers', name='계획', line=dict(color='#cbd5e1', width=2, dash='dash'), marker=dict(color='#cbd5e1'), hovertemplate='%{y:,.0f}백만<extra></extra>'))
fig_line.add_trace(go.Scatter(x=months_dates, y=principals, mode='lines+markers', name='원금', line=dict(color='#3b82f6', width=3), marker=dict(size=6), hovertemplate='%{y:,.0f}백만<extra></extra>'))
fig_line.add_trace(go.Scatter(x=months_dates, y=evaluations, mode='lines+markers', name='평가액', line=dict(color='#10b981', width=3), marker=dict(size=6), hovertemplate='%{y:,.0f}백만<extra></extra>'))

fig_line.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(
        showgrid=False, 
        tickfont=dict(color="#64748b", size=11),
        tickformat="%y.%m",
        dtick="M1",  # 1개월 단위
        title_font=dict(size=12, color="#64748b"),
        fixedrange=True
    ),
    yaxis=dict(
        showgrid=True, 
        gridcolor="#f1f5f9", 
        tickfont=dict(color="#64748b", size=11), 
        tickformat=",.0f",
        title="단위: 백만원",
        title_font=dict(size=11, color="#94a3b8"),
        fixedrange=True
    ),
    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=12, color="#475569")),
    margin=dict(l=10, r=10, t=10, b=10),
    height=320,
    width=max(800, len(months_dates) * 60), # 숫자 4개(약 60px) 너비 고정
    hovermode="x unified"
)
st.plotly_chart(fig_line, use_container_width=False, config={"displayModeBar": False, "scrollZoom": False})

draw_neon_divider()

# ── 월 선택 (상태 관리 및 좌우 이동 버튼) ─────────────────
if "global_year" not in st.session_state:
    st.session_state.global_year = now.year
if "global_month" not in st.session_state:
    st.session_state.global_month = now.month

def prev_month():
    if st.session_state.global_month == 1:
        st.session_state.global_month = 12
        st.session_state.global_year -= 1
    else:
        st.session_state.global_month -= 1

def next_month():
    if st.session_state.global_month == 12:
        st.session_state.global_month = 1
        st.session_state.global_year += 1
    else:
        st.session_state.global_month += 1

year = st.session_state.global_year
month = st.session_state.global_month

# ── 월 선택 (좌우 이동 버튼) ─────────────────────────
nav_container = st.container()
with nav_container:
    st.button("◀", on_click=prev_month)
    st.markdown(f"""
    <div id="month-nav-marker" style='display: flex; align-items: center; justify-content: center; height: 42px; width: 140px; font-size: 1.2rem; font-weight: 700; color: #1e293b; margin: 0 auto;'>
        <span style="transform: translateY(-4px);">{year}년 {month}월</span>
    </div>
    """, unsafe_allow_html=True)
    st.button("▶", on_click=next_month)

draw_neon_divider()


# ── 데이터 로드 ───────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    s = get_monthly_summary(year, month)
    goal_data = get_monthly_goal(year, month)

ti   = s["total_income"]
tf   = s["total_fixed"]
tv   = s["total_variable"]
tu   = s["total_utility"]
te   = s["total_expense"]
net  = s["net"]
cat  = s["category_totals"]
tinv = s["total_investment"]
t_asset = s.get("total_principal") or 0 
cash_asset = sum((inv.get("principal") or 0) for inv in s.get("investments", []) if inv.get("account_type") in INVESTMENT_ACCOUNTS.get("현금성 자산", []))

# ── KPI 카드 (모바일 최적화 Grid) ──────────────────────────
delta_str = "▲ 흑자" if net >= 0 else "▼ 적자"
is_positive = "▲" in delta_str or "흑자" in delta_str
delta_color = "#10b981" if is_positive else "#ef4444"

grid_html = f"""<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(4px, 1.5vw, 10px); margin-bottom: 10px;">
<div>{_get_card_html("총 수입", f"₩{ti:,.0f}", "", "#ff6b00")}</div>
<div>{_get_card_html("고정비", f"₩{tf:,.0f}", "", "#475569")}</div>
<div>{_get_card_html("변동비", f"₩{tv + tu:,.0f}", "", "#94a3b8")}</div>
</div>
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(4px, 1.5vw, 10px); margin-bottom: 5px;">
<div>{_get_card_html("잔여금", f"₩{net:,.0f}", delta_str, "#1b263b", delta_color)}</div>
<div>{_get_card_html("현금성 자산", f"₩{cash_asset:,.0f}", "", "#8b5cf6")}</div>
<div>{_get_card_html("총 자산", f"₩{t_asset:,.0f}", "", "#3b82f6")}</div>
</div>
<div style="text-align: right; font-size: 0.8rem; color: #64748b; margin-bottom: 20px;">
* 금액 기준은 평가액이 아닌, 원금 기준임
</div>"""
st.markdown(grid_html, unsafe_allow_html=True)

draw_neon_divider()

# ── 카테고리별 요약 카드 (전월비 포함) ──────────────────────────────
from utils.db import CATEGORIES, get_monthly_income, get_fixed_costs, get_utility_costs, get_other_incomes

_cat_colors = ["#ff6b00", "#1b263b", "#3b82f6", "#94a3b8", "#f97316", "#475569"]
_txns = get_transactions(year, month)

_cat_sum = {}
if _txns:
    _cat_sum = {c: 0 for c in CATEGORIES}
    for _t in _txns:
        _cat_sum[_t["category"]] = _cat_sum.get(_t["category"], 0) + _t["amount"]
    _total_v = sum(_t["amount"] for _t in _txns)
    _cat_items = sorted(_cat_sum.items(), key=lambda x: -x[1])

    _prev_m = month - 1 if month > 1 else 12
    _prev_y = year if month > 1 else year - 1
    _prev_txns = get_transactions(_prev_y, _prev_m)
    _prev_cat_sum = {}
    if _prev_txns:
        for _t in _prev_txns:
            _prev_cat_sum[_t["category"]] = _prev_cat_sum.get(_t["category"], 0) + _t["amount"]
    _prev_total_v = sum(_t["amount"] for _t in _prev_txns) if _prev_txns else 0

    def _mom_badge(curr, prev):
        if prev == 0 and curr == 0:
            return "<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#f8fafc;color:#94a3b8;font-size:0.75rem;font-weight:700;'>- 변동 없음</div>"
        delta = curr - prev
        if delta > 0:
            return f"<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#fee2e2;color:#ef4444;font-size:0.75rem;font-weight:700;'>+{delta:,}원</div>"
        elif delta < 0:
            return f"<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#dcfce7;color:#16a34a;font-size:0.75rem;font-weight:700;'>{delta:,}원</div>"
        else:
            return "<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#f8fafc;color:#94a3b8;font-size:0.75rem;font-weight:700;'>- 변동 없음</div>"

    _cards_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;'>"
    for _idx, (_cat, _amt) in enumerate(_cat_items):
        if _amt == 0:
            continue
        _color = _cat_colors[_idx % len(_cat_colors)]
        _badge = _mom_badge(_amt, _prev_cat_sum.get(_cat, 0))
        _cards_html += f"""
        <div style='background:#fff;border:1px solid #e2e8f0;border-radius:12px;
                    padding:14px 16px;min-width:110px;flex:1;
                    box-shadow:0 4px 12px rgba(0,0,0,0.03);text-align:center;'>
          <div style='width:24px;height:3px;background:{_color};border-radius:2px;margin:0 auto 8px;'></div>
          <div style='font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:6px;'>{_cat}</div>
          <div style='font-size:1.1rem;font-weight:800;color:#1e293b;'>&#8361;{_amt:,}</div>
          {_badge}
        </div>"""

    _tot_badge = _mom_badge(_total_v, _prev_total_v)
    _cards_html += f"""
        <div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;
                    padding:14px 16px;min-width:130px;flex:1;
                    box-shadow:0 4px 12px rgba(0,0,0,0.03);text-align:center;'>
          <div style='width:24px;height:3px;background:#ff6b00;border-radius:2px;margin:0 auto 8px;'></div>
          <div style='font-size:0.75rem;color:#ff6b00;font-weight:600;margin-bottom:6px;'>변동지출 합계</div>
          <div style='font-size:1.15rem;font-weight:800;color:#ff6b00;'>&#8361;{_total_v:,}</div>
          {_tot_badge}
        </div>"""
    _cards_html += "</div>"
    st.markdown(_cards_html, unsafe_allow_html=True)

    draw_neon_divider()

    # ── 변동지출 구성 도넛 차트 ──────────────────────────────
    if _cat_sum:
        _cat_for_pie = {k: v for k, v in _cat_sum.items() if v > 0}
        if _cat_for_pie:
            _fig_pie = px.pie(
                values=list(_cat_for_pie.values()),
                names=list(_cat_for_pie.keys()),
                color_discrete_sequence=["#ff6b00", "#1b263b", "#f97316", "#3b82f6", "#94a3b8", "#cbd5e1", "#8b5cf6", "#ec4899"],
                color_discrete_map={"준영점심": "#10b981"},
                hole=0.5,
            )
            _fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                marker=dict(line=dict(color='#ffffff', width=4))
            )
            _fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", font_color="#475569",
                height=320, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(font=dict(size=11), orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
            )
            st.plotly_chart(_fig_pie, use_container_width=True)

draw_neon_divider()


# ── 🎯 현금성 자산 목표 진척도 ──────────────────────────────────
target_amount = goal_data.get("target_amount") if goal_data else 0
target_amount = int(target_amount) if target_amount else 0

if target_amount > 0:
    progress_pct = (cash_asset / target_amount) * 100
    if progress_pct > 100: progress_pct = 100
    
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
            <span style="font-size: 1.1rem; font-weight: 700; color: #1e293b;">🎯 {year}년 {month}월 현금성 자산 목표 진척도</span>
            <span style="font-size: 0.95rem; font-weight: 600; color: #3b82f6;">{progress_pct:.1f}%</span>
        </div>
        <div style="width: 100%; background-color: #e2e8f0; border-radius: 9999px; height: 12px; overflow: hidden; margin-bottom: 8px;">
            <div style="background-color: #3b82f6; height: 12px; border-radius: 9999px; width: {progress_pct}%; transition: width 0.5s ease-in-out;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #64748b;">
            <span>현재: ₩{cash_asset:,.0f}</span>
            <span>목표: ₩{target_amount:,.0f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("🎯 설정 메뉴에서 이달의 자산 목표를 설정하여 진척도를 확인해 보세요.")


