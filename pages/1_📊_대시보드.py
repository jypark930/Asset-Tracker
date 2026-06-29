"""
pages/1_📊_대시보드.py  ─  자산 현황 메인 대시보드
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="대시보드", page_icon="📊", layout="wide")

from utils.auth import is_authenticated, get_current_user, try_restore_session, EMAIL_TO_NAME
from utils.db import get_monthly_summary, get_transactions, get_monthly_goal, INVESTMENT_ACCOUNTS

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
<div style="font-size: clamp(0.85rem, 3.5vw, 1.35rem);font-weight:800;color:{value_color};font-family:'KoPubWorldBold',monospace;line-height:1.2;letter-spacing:-0.5px;white-space:nowrap;">{value}</div>
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


# ── 월 선택 (상태 관리 및 좌우 이동 버튼) ─────────────────────────
if "dash_year" not in st.session_state:
    st.session_state.dash_year = now.year
if "dash_month" not in st.session_state:
    st.session_state.dash_month = now.month

def prev_month():
    if st.session_state.dash_month == 1:
        st.session_state.dash_month = 12
        st.session_state.dash_year -= 1
    else:
        st.session_state.dash_month -= 1

def next_month():
    if st.session_state.dash_month == 12:
        st.session_state.dash_month = 1
        st.session_state.dash_year += 1
    else:
        st.session_state.dash_month += 1

year = st.session_state.dash_year
month = st.session_state.dash_month

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
t_asset = s.get("total_principal", 0) 
cash_asset = sum(inv.get("principal", 0) for inv in s.get("investments", []) if inv.get("account_type") in INVESTMENT_ACCOUNTS.get("현금성 자산", []))

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

# ── 🎯 자산 목표 진척도 ──────────────────────────────────
target_amount = goal_data.get("target_amount", 0) if goal_data else 0

if target_amount > 0:
    progress_pct = (t_asset / target_amount) * 100
    if progress_pct > 100: progress_pct = 100
    
    st.markdown(f"""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
            <span style="font-size: 1.1rem; font-weight: 700; color: #1e293b;">🎯 {year}년 {month}월 총 자산 목표 진척도</span>
            <span style="font-size: 0.95rem; font-weight: 600; color: #3b82f6;">{progress_pct:.1f}%</span>
        </div>
        <div style="width: 100%; background-color: #e2e8f0; border-radius: 9999px; height: 12px; overflow: hidden; margin-bottom: 8px;">
            <div style="background-color: #3b82f6; height: 12px; border-radius: 9999px; width: {progress_pct}%; transition: width 0.5s ease-in-out;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #64748b;">
            <span>현재: ₩{t_asset:,.0f}</span>
            <span>목표: ₩{target_amount:,.0f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("🎯 설정 메뉴에서 이달의 자산 목표를 설정하여 진척도를 확인해 보세요.")

draw_neon_divider()


# ── 변동지출 구성 파이 차트 (막대 차트 제거, 간격 띄움) ─────
st.markdown("<p style='font-size:1.1rem;font-weight:600;color:#94a3b8;margin-bottom:8px;'>🍰 변동지출 구성</p>", unsafe_allow_html=True)
if cat:
    fig2 = px.pie(
        values=list(cat.values()),
        names=list(cat.keys()),
        color_discrete_sequence=["#ff6b00", "#1b263b", "#f97316", "#3b82f6", "#94a3b8", "#cbd5e1", "#8b5cf6", "#ec4899"],
        color_discrete_map={"준영점심": "#10b981"},
        hole=0.5,
    )
    # pull을 제거하고, 대신 배경색과 동일한 아주 두꺼운 테두리를 넣어 간격이 100% 일정하게 보이도록 수정
    fig2.update_traces(
        textposition="inside", 
        textinfo="percent+label",
        marker=dict(line=dict(color='#ffffff', width=4))
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color="#475569",
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(font=dict(size=11), orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Plotly 파이 차트의 클릭 이벤트 미지원 한계로 인해, pills(알약 모양 버튼)를 사용한 필터링 제공
    categories = list(cat.keys())
    selected_pill = st.pills("🔍 카테고리를 선택하여 내역을 필터링하세요:", options=["🌟 전체보기"] + categories, default="🌟 전체보기")
    
    selected_category = None
    if selected_pill and selected_pill != "🌟 전체보기":
        selected_category = selected_pill

else:
    st.info("📌 변동지출 데이터가 없습니다.")
    selected_category = None

draw_neon_divider()


# ── 변동지출 내역 ──────────────────────
if selected_category:
    st.markdown(f"<p style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:8px;'>🧾 {year}년 {month}월 <span style='color:#ff6b00;'>[{selected_category}]</span> 지출 내역</p>", unsafe_allow_html=True)
else:
    st.markdown(f"<p style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:8px;'>🧾 {year}년 {month}월 전체 변동지출 내역</p>", unsafe_allow_html=True)

txns = get_transactions(year, month)
if txns:
    df = pd.DataFrame(txns)[["day", "category", "description", "amount"]]
    df.columns = ["일", "구분", "이용처", "금액(원)"]
    
    # 선택된 카테고리가 있으면 필터링
    if selected_category:
        df = df[df["구분"] == selected_category]
        
    if len(df) > 0:
        sum_amt = df["금액(원)"].sum()
        df["금액(원)"] = df["금액(원)"].apply(lambda x: f"₩{x:,}")
        
        # 커스텀 HTML 테이블 (중앙 정렬 및 완벽한 너비 조절)
        html = "<div style='overflow-x: auto;'>"
        html += "<table style='width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95rem; text-align: center; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.03); font-family: \"KoPubWorldDotum\", sans-serif;'>"
        html += "<tr style='background-color: #f8f9fa; border-bottom: 2px solid #e2e8f0; color: #64748b; font-weight: 700;'>"
        html += "<th style='padding: 12px 8px; width: 16%; text-align: center;'>일</th>"
        html += "<th style='padding: 12px 8px; width: 22%; text-align: center;'>구분</th>"
        html += "<th style='padding: 12px 8px; text-align: center;'>이용처</th>"
        html += "<th style='padding: 12px 12px; width: 1%; white-space: nowrap; text-align: center;'>금액(원)</th>"
        html += "</tr>"
        
        for idx, row in df.iterrows():
            html += "<tr style='border-bottom: 1px solid #f1f5f9; background-color: #ffffff;'>"
            html += f"<td style='padding: 12px 8px; width: 16%; color: #1e293b; font-weight: 700;'>{row['일']}</td>"
            html += f"<td style='padding: 12px 8px; width: 22%; color: #475569;'>{row['구분']}</td>"
            html += f"<td style='padding: 12px 8px; color: #1e293b;'>{row['이용처']}</td>"
            html += f"<td style='padding: 12px 12px; width: 1%; white-space: nowrap; color: #1e293b; text-align: right; font-weight: 600;'>{row['금액(원)']}</td>"
            html += "</tr>"
            
        html += "</table></div>"
        st.markdown(html, unsafe_allow_html=True)
        
        st.caption(f"총 {len(df)}건 / 합계 ₩{sum_amt:,}")
    else:
        st.info(f"📌 '{selected_category}' 카테고리의 지출 내역이 없습니다.")
else:
    st.info("📌 변동지출 내역이 없습니다. 가계부 메뉴에서 입력하세요.")
