"""
pages/3_📈_투자현황.py  ─  투자 자산 현황 관리
"""
import streamlit as st
from utils.db import get_investments, upsert_investment, replace_investment_stocks, get_all_investment_stocks
from utils.auth import get_supabase_client
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="투자현황 | Asset Tracker", page_icon="📈", layout="wide")

from utils.auth import is_authenticated, try_restore_session, get_current_user
from utils.db import INVESTMENT_ACCOUNTS, get_investments, upsert_investment, get_monthly_income, upsert_monthly_income, get_all_investment_stocks, replace_investment_stocks, copy_previous_month_investments

CUSTOM_SORT_ORDER = [
    "Nh투자증권우", "NH투자증권우",
    "대신증권우",
    "LG화학우",
    "삼성화재우",
    "한국투자 ACE 고배당주증권 ETF", "ACE 고배당주",
    "현대차우",
    "KB금융",
    "BITO",
    "CONY",
    "코인베이스 글로벌", "코인베이스",
    "ETHU",
    "레드와이어",
    "Invesco QQQ Trust Series 1", "QQQ",
    "iShares Semiconductor ETF", "SOXX",
    "기업은행",
    "현대차2우B",
    "TIGER코스닥150",
    "코리안리",
    "서울보증보험",
    "우리금융지주",
    "KODEX미국배당커버드콜",
    "CJ우",
    "SK",
    "NAVER"
]


if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("0_🏠_홈.py")

now = datetime.now()


# ── 커스텀 타이틀 ─────────────────────────
st.markdown("""
<div style="width:100%;display:flex;justify-content:center;margin-bottom:4px;margin-top:10px;">
    <h1 style="font-size:1.8rem;font-weight:800;color:#1e293b;margin:0 auto;text-align:center !important;width:100%;">
        투자 현황
    </h1>
</div>
""", unsafe_allow_html=True)

def _get_card_html(title: str, value: str, delta: str = "", border_color: str = "#ff6b00", delta_color: str = "#10b981"):
    delta_html = f"<div style='font-size: clamp(0.65rem, 2.5vw, 0.8rem);font-weight:600;color:{delta_color};margin-top:4px;white-space:nowrap;'>{delta}</div>" if delta else ""
    return f"""<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: clamp(10px, 2.5vw, 20px) clamp(4px, 1.5vw, 14px); box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; overflow: hidden;">
<div style="width: 24px; height: 3px; background-color: {border_color}; border-radius: 2px; margin-bottom: clamp(6px, 2vw, 12px);"></div>
<div style="font-size: clamp(0.65rem, 2.5vw, 0.8rem);color:#64748b;font-weight:600;letter-spacing:0.02em;margin-bottom:6px;white-space:nowrap;">{title}</div>
<div style="font-size: clamp(0.85rem, 3.5vw, 1.35rem);font-weight:800;color:#1e293b;font-family:'KoPubWorldBold',monospace;line-height:1.2;letter-spacing:-0.5px;white-space:nowrap;">{value}</div>
{delta_html}
</div>"""

def draw_light_divider():
    st.markdown('<hr style="height:1px;border:none;background:#e2e8f0;margin:16px 0;">', unsafe_allow_html=True)

# ── 월 선택 (◄ ► 네비게이션) ────────────────────────
if "global_year" not in st.session_state:
    st.session_state.global_year = now.year
if "global_month" not in st.session_state:
    st.session_state.global_month = now.month

def inv_prev_month():
    if st.session_state.global_month == 1:
        st.session_state.global_month = 12
        st.session_state.global_year -= 1
    else:
        st.session_state.global_month -= 1

def inv_next_month():
    if st.session_state.global_month == 12:
        st.session_state.global_month = 1
        st.session_state.global_year += 1
    else:
        st.session_state.global_month += 1

year  = st.session_state.global_year
month = st.session_state.global_month

nav_container = st.container()
with nav_container:
    st.button("◀", on_click=inv_prev_month, key="inv_prev_btn")
    st.markdown(f"""
    <div id="month-nav-marker" style='display: flex; align-items: center; justify-content: center; height: 42px; width: 140px; font-size: 1.2rem; font-weight: 700; color: #1e293b; margin: 0 auto;'>
        <span style="transform: translateY(-4px);">{year}년 {month}월</span>
    </div>
    """, unsafe_allow_html=True)
    st.button("▶", on_click=inv_next_month, key="inv_next_btn")

is_past_month    = (year < now.year) or (year == now.year and month < now.month)
is_current_month = (year == now.year and month == now.month)
inc = get_monthly_income(year, month)
confirmed_fields = inc.get("confirmed_fields", []) if inc and "confirmed_fields" in inc else []
is_closed = "investments_closed" in confirmed_fields

if is_past_month:
    user = get_current_user()
    is_admin = user and user.email == "jypark930@naver.com"
    close_disabled = is_closed and not is_admin
    new_status = st.radio("마감 여부", ["Y", "N"], index=0 if is_closed else 1,
                          horizontal=True, disabled=close_disabled, key=f"close_radio_{year}_{month}")
    if (new_status == "Y") != is_closed:
        if new_status == "Y":
            if "investments_closed" not in confirmed_fields:
                confirmed_fields.append("investments_closed")
        else:
            if "investments_closed" in confirmed_fields:
                confirmed_fields.remove("investments_closed")
        upsert_monthly_income(year, month, inc if inc else {}, confirmed_fields=confirmed_fields)
        st.rerun()

draw_light_divider()

# ── 데이터 로드 및 집계 ───────────────────────────────────────────
if copy_previous_month_investments(year, month):
    st.toast("전월 투자 자산 및 상세 종목 내역을 성공적으로 복사해 왔습니다! 🚀", icon="✅")

invests = get_investments(year, month)
all_inv_ids = [i["id"] for i in invests]
all_stocks = get_all_investment_stocks(all_inv_ids)

inv_map = {(i["owner"], i["account_type"]): {"amount": i.get("amount", 0), "principal": i.get("principal", 0)} for i in invests}

from utils.currency import get_usd_krw_rate

# 계좌명, 종목명 기준으로 종목 데이터를 그룹화 (수량, 원금, 평가액 등)
stock_map = {}
usd_rate = get_usd_krw_rate()

for s in all_stocks:
    inv = next((i for i in invests if i["id"] == s["investment_id"]), None)
    if not inv: continue
    owner = inv["owner"]
    acc = inv["account_type"]
    name = s["stock_name"]
    qty = s.get("quantity", 0)
    principal = s.get("principal", 0)
    valuation = s.get("valuation", 0)
    
    # 예수금(현금) 이름은 예수금(원화)로 마이그레이션 처리
    if name == "예수금(현금)":
        name = "예수금(원화)"
        
    # 달러 예수금의 경우 실시간 환율 적용
    if acc == "총 예수금" and name == "예수금(달러)":
        valuation = float(qty) * usd_rate
        principal = float(qty) * usd_rate
    
    if (acc, name) not in stock_map:
        stock_map[(acc, name)] = {"jy_p": 0, "jy_a": 0, "ji_p": 0, "ji_a": 0, "jy_qty": 0.0, "ji_qty": 0.0}
        
    if owner == "준영":
        stock_map[(acc, name)]["jy_p"] += principal
        stock_map[(acc, name)]["jy_a"] += valuation
        stock_map[(acc, name)]["jy_qty"] += float(qty)
    else:
        stock_map[(acc, name)]["ji_p"] += principal
        stock_map[(acc, name)]["ji_a"] += valuation
        stock_map[(acc, name)]["ji_qty"] += float(qty)

# 종목이 등록된 계좌의 경우, 하위 종목들의 합계로 전체 계좌 데이터를 덮어씌움
for owner in ["준영", "지윤"]:
    p_key, a_key = ("jy_p", "jy_a") if owner == "준영" else ("ji_p", "ji_a")
    qty_key = "jy_qty" if owner == "준영" else "ji_qty"
    
    acc_sums = {}
    for (acc, name), d in stock_map.items():
        if d[qty_key] > 0 or d[p_key] > 0 or d[a_key] > 0:
            if acc not in acc_sums:
                acc_sums[acc] = {"p": 0, "a": 0}
            acc_sums[acc]["p"] += d[p_key]
            acc_sums[acc]["a"] += d[a_key]
            
    for acc, sums in acc_sums.items():
        inv_map[(owner, acc)] = {"principal": sums["p"], "amount": sums["a"]}
        for i in invests:
            if i["owner"] == owner and i["account_type"] == acc:
                i["principal"] = sums["p"]
                i["amount"] = sums["a"]


def calc_pnl(principal, amount):
    if principal == 0:
        return 0.0
    return (amount - principal) / principal * 100

def format_pnl(pnl):
    if pnl == 0.0:
        return f"<span style='color: gray;'>0.0%</span>"
    color = "#f87171" if pnl > 0 else "#60a5fa"
    sign = "+" if pnl > 0 else ""
    return f"<span style='color: {color}; font-weight: bold;'>{sign}{pnl:.1f}%</span>"

def get_row_data(acc_type):
    jy_p = inv_map.get(("준영", acc_type), {}).get("principal", 0)
    jy_a = inv_map.get(("준영", acc_type), {}).get("amount", 0)
    ji_p = inv_map.get(("지윤", acc_type), {}).get("principal", 0)
    ji_a = inv_map.get(("지윤", acc_type), {}).get("amount", 0)
    
    tot_p = jy_p + ji_p
    tot_a = jy_a + ji_a
    
    return {
        "tot_p": tot_p, "tot_a": tot_a, "tot_pnl": calc_pnl(tot_p, tot_a),
        "jy_p": jy_p, "jy_a": jy_a, "jy_pnl": calc_pnl(jy_p, jy_a),
        "ji_p": ji_p, "ji_a": ji_a, "ji_pnl": calc_pnl(ji_p, ji_a),
    }

def get_stock_row_data(acc_type, name):
    d = stock_map[(acc_type, name)]
    tot_p = d["jy_p"] + d["ji_p"]
    tot_a = d["jy_a"] + d["ji_a"]
    return {
        "tot_p": tot_p, "tot_a": tot_a, "tot_pnl": calc_pnl(tot_p, tot_a),
        "jy_p": d["jy_p"], "jy_a": d["jy_a"], "jy_pnl": calc_pnl(d["jy_p"], d["jy_a"]),
        "ji_p": d["ji_p"], "ji_a": d["ji_a"], "ji_pnl": calc_pnl(d["ji_p"], d["ji_a"]),
    }

def build_tr(label, data, is_bold=False, indent=0, bg_color=""):
    style = ""
    if bg_color:
        style += f"background-color: {bg_color}; "
    if is_bold:
        style += "font-weight: bold; "
    
    pad = 10 + (indent * 20)
    
    def fmt(val):
        return f"{int(round(val)):,}" if val != 0 else "-"
        
    return f"""<tr style="{style}">
<td style="padding-left: {pad}px;">{label}</td>
<td style="text-align: right;">{fmt(data['tot_p'])}</td>
<td style="text-align: right;">{fmt(data['tot_a'])}</td>
<td style="text-align: right;">{format_pnl(data['tot_pnl'])}</td>
<td style="text-align: right;">{fmt(data['jy_p'])}</td>
<td style="text-align: right;">{fmt(data['jy_a'])}</td>
<td style="text-align: right;">{format_pnl(data['jy_pnl'])}</td>
<td style="text-align: right;">{fmt(data['ji_p'])}</td>
<td style="text-align: right;">{fmt(data['ji_a'])}</td>
<td style="text-align: right;">{format_pnl(data['ji_pnl'])}</td>
</tr>"""

# 데이터 집계 로직
non_cash_list = INVESTMENT_ACCOUNTS["비현금성 자산"]
cash_list = INVESTMENT_ACCOUNTS["현금성 자산"]

non_cash_data = {"tot_p":0, "tot_a":0, "jy_p":0, "jy_a":0, "ji_p":0, "ji_a":0}
for acc in non_cash_list:
    d = get_row_data(acc)
    for k in ["tot_p", "tot_a", "jy_p", "jy_a", "ji_p", "ji_a"]: non_cash_data[k] += d[k]
non_cash_data["tot_pnl"] = calc_pnl(non_cash_data["tot_p"], non_cash_data["tot_a"])
non_cash_data["jy_pnl"]  = calc_pnl(non_cash_data["jy_p"], non_cash_data["jy_a"])
non_cash_data["ji_pnl"]  = calc_pnl(non_cash_data["ji_p"], non_cash_data["ji_a"])

cash_data = {"tot_p":0, "tot_a":0, "jy_p":0, "jy_a":0, "ji_p":0, "ji_a":0}
for acc in cash_list:
    d = get_row_data(acc)
    for k in ["tot_p", "tot_a", "jy_p", "jy_a", "ji_p", "ji_a"]: cash_data[k] += d[k]
cash_data["tot_pnl"] = calc_pnl(cash_data["tot_p"], cash_data["tot_a"])
cash_data["jy_pnl"]  = calc_pnl(cash_data["jy_p"], cash_data["jy_a"])
cash_data["ji_pnl"]  = calc_pnl(cash_data["ji_p"], cash_data["ji_a"])

total_data = {k: non_cash_data[k] + cash_data[k] for k in ["tot_p", "tot_a", "jy_p", "jy_a", "ji_p", "ji_a"]}
total_data["tot_pnl"] = calc_pnl(total_data["tot_p"], total_data["tot_a"])
total_data["jy_pnl"]  = calc_pnl(total_data["jy_p"], total_data["jy_a"])
total_data["ji_pnl"]  = calc_pnl(total_data["ji_p"], total_data["ji_a"])

# ── KPI 카드 ──────────────────────────────────────────────
tot_pnl_amt = total_data["tot_a"] - total_data["tot_p"]
tot_pnl_sign = "+" if tot_pnl_amt >= 0 else ""
delta_text = f"{tot_pnl_sign}{int(round(tot_pnl_amt)):,}원 ({total_data['tot_pnl']:.1f}%)"
delta_color = "#10b981" if tot_pnl_amt >= 0 else "#ef4444"

jy_pnl_amt = total_data["jy_a"] - total_data["jy_p"]
jy_pnl_sign = "+" if jy_pnl_amt >= 0 else ""
jy_delta = f"{jy_pnl_sign}{int(round(jy_pnl_amt)):,}원 ({total_data['jy_pnl']:.1f}%)"
jy_color = "#10b981" if jy_pnl_amt >= 0 else "#ef4444"

ji_pnl_amt = total_data["ji_a"] - total_data["ji_p"]
ji_pnl_sign = "+" if ji_pnl_amt >= 0 else ""
ji_delta = f"{ji_pnl_sign}{int(round(ji_pnl_amt)):,}원 ({total_data['ji_pnl']:.1f}%)"
ji_color = "#10b981" if ji_pnl_amt >= 0 else "#ef4444"

grid_html = f"""<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(4px, 1.5vw, 10px); margin-bottom: 8px;">
<div>{_get_card_html("총 자산 평가액", f"₩{int(round(total_data['tot_a'])):,}", delta_text, "#1b263b", delta_color)}</div>
<div>{_get_card_html("👨 준영 자산", f"₩{int(round(total_data['jy_a'])):,}", jy_delta, "#3b82f6", jy_color)}</div>
<div>{_get_card_html("👩 지윤 자산", f"₩{int(round(total_data['ji_a'])):,}", ji_delta, "#f472b6", ji_color)}</div>
</div>
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(4px, 1.5vw, 10px); margin-bottom: 20px;">
<div>{_get_card_html("총 현금성 자산 원금", f"₩{int(round(total_data['tot_p'])):,}", "", "#1b263b", "")}</div>
<div>{_get_card_html("👨 준영 원금", f"₩{int(round(total_data['jy_p'])):,}", "", "#3b82f6", "")}</div>
<div>{_get_card_html("👩 지윤 원금", f"₩{int(round(total_data['ji_p'])):,}", "", "#f472b6", "")}</div>
</div>"""
st.markdown(grid_html, unsafe_allow_html=True)
st.markdown("<p style='font-size:0.8rem;color:#94a3b8;margin-top:-8px;margin-bottom:4px;'>* 자산은 원금 기준임</p>", unsafe_allow_html=True)
draw_light_divider()

# ── 자산 구성 요약 + 계좌별 상세 (탭 통합) ────────────────────
st.markdown(f"<p style='font-size:1.3rem;font-weight:700;color:#1e293b;margin-bottom:8px;'>자산 구성 비중 <span style='font-size:1.1rem;color:#64748b;font-weight:600;'>(총 원금: ₩{int(round(total_data['tot_p'])):,})</span></p>", unsafe_allow_html=True)
if invests and total_data["tot_p"] > 0:
    import plotly.graph_objects as go
    tab_fam, tab_jy, tab_ji = st.tabs(["\U0001f31f 가족 전체", "\U0001f468 준영", "\U0001f469 지윤"])

    def _draw_pie_tab(owner_name, tot_amt, cash_amt, non_cash_amt, is_total=False):
        if tot_amt <= 0:
            st.info(f"{owner_name} 자산 데이터가 없습니다.")
            return
            
        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        with c1:
            if is_total:
                labels = ["현금성 자산", "비현금성 자산"]
                values = [cash_amt, non_cash_amt]
                colors = ["#3b82f6", "#ff6b00"]
            else:
                data = [(i["account_type"], i.get("principal", 0)) for i in invests if i["owner"] == owner_name and i.get("principal", 0) > 0]
                acc_order = ["TOSS", "KB", "총 예수금", "CMA", "업비트", "청년도약", "주택청약", "IRP", "중개형ISA"]
                data = sorted(data, key=lambda x: acc_order.index(x[0]) if x[0] in acc_order else 999)
                labels, values = zip(*data) if data else (["데이터없음"],[1])
                acc_color_map = {
                    "TOSS": "#3b82f6", "KB": "#f59e0b", "총 예수금": "#10b981", 
                    "CMA": "#8b5cf6", "업비트": "#f43f5e", "청년도약": "#0ea5e9",
                    "주택청약": "#ff6b00", "IRP": "#84cc16", "중개형ISA": "#ec4899"
                }
                colors = [acc_color_map.get(lbl, "#94a3b8") for lbl in labels] if data else ["#e2e8f0"]

            fig = go.Figure(go.Pie(
                labels=labels, values=values, sort=False, direction='clockwise',
                hole=0.45, marker_colors=colors, textinfo="percent+label", textposition="inside",
                insidetextorientation="horizontal"
            ))
            fig.update_traces(marker=dict(line=dict(color='#ffffff', width=3)))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#475569", height=280, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.markdown(f"""
            <div style='background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-top:12px;'>
                <div style='margin-bottom:8px; font-size:1.05rem;'><span style='color:#3b82f6;'>\U0001f4b0</span> <b>현금성 자산</b>: \u20a9{int(round(cash_amt)):,} <span style='color:#64748b;font-size:0.9rem;'>({cash_amt/tot_amt*100:.1f}%)</span></div>
                <div style='font-size:1.05rem;'><span style='color:#ff6b00;'>\U0001f3e0</span> <b>비현금성 자산</b>: \u20a9{int(round(non_cash_amt)):,} <span style='color:#64748b;font-size:0.9rem;'>({non_cash_amt/tot_amt*100:.1f}%)</span></div>
                <div style='font-size:0.78rem;color:#94a3b8;margin-top:10px;'>* 자산은 원금 기준임</div>
            </div>
            """, unsafe_allow_html=True)


# investment_id → stocks 매핑
inv_stocks_map = {}
for s in all_stocks:
    iid = s["investment_id"]
    if iid not in inv_stocks_map:
        inv_stocks_map[iid] = []
    inv_stocks_map[iid].append(s)

SKIP_STOCK_NAMES = {"예수금(원화)", "예수금(달러)", "예수금(현금)", "예수금", "보유금액", "주택청약", "청년도약"}
# 종목 입력 가능한 계좌 목록
STOCK_INPUT_ACCOUNTS = ["총 예수금", "중개형ISA", "IRP", "KB", "TOSS", "업비트"]
PRINCIPAL_ONLY_ACCOUNTS = ["총 예수금", "CMA", "청년도약"]  # 원금만 수정 가능한 계좌

def render_detail_table(owner_key, prefix="", show_stocks=False):
    owner_invs = [i for i in invests if i["owner"] == owner_key]
    if not owner_invs:
        st.info(f"{owner_key}님의 등록된 자산이 없습니다.")
        return

    sort_order = {"TOSS": 1, "중개형ISA": 2, "KB": 3, "총 예수금": 4,
                  "CMA": 5, "청년도약": 6, "주택청약": 7, "IRP": 8, "업비트": 9}
    owner_invs.sort(key=lambda x: sort_order.get(x["account_type"], 99))

    cash_invs = [i for i in owner_invs if i["account_type"] in INVESTMENT_ACCOUNTS["현금성 자산"]]
    non_cash_invs = [i for i in owner_invs if i["account_type"] not in INVESTMENT_ACCOUNTS["현금성 자산"]]

    def _render_group(title, icon, invs):
        if not invs: return
        grp_p = sum(i.get("principal", 0) for i in invs)
        grp_a = sum(i.get("amount", 0) for i in invs)
        grp_pnl_amt = grp_a - grp_p
        grp_pnl_pct = calc_pnl(grp_p, grp_a)
        grp_sign = "+" if grp_pnl_amt > 0 else ""
        grp_color = "#ef4444" if grp_pnl_amt > 0 else "#3b82f6" if grp_pnl_amt < 0 else "#64748b"
        st.markdown(f"""
        <div style='margin-top:20px;margin-bottom:12px;border-bottom:2px solid #e2e8f0;padding-bottom:8px;'>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <h5 style="margin:0;color:#334155;font-size:1.35rem;font-weight:800;">{icon} {title}</h5>
                <span style="font-size:1.05rem;font-weight:700;color:{grp_color};">{grp_sign}{int(round(grp_pnl_amt)):,} ({grp_sign}{grp_pnl_pct:.1f}%)</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:0.9rem;color:#64748b;font-weight:500;">원금: {int(round(grp_p)):,}원</span>
                <span style="font-size:1.05rem;font-weight:700;color:#1e293b;">평가액: {int(round(grp_a)):,}원</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        def get_sort_key(s):
            sname = s.get("stock_name", "")
            try: return (0, CUSTOM_SORT_ORDER.index(sname))
            except: return (1, -s.get("valuation", 0))

        for inv in invs:
            acc_type = inv["account_type"]
            stocks = inv_stocks_map.get(inv["id"], [])
            real_stocks = [s for s in stocks if s.get("stock_name", "") not in SKIP_STOCK_NAMES]
            tot_p = inv.get("principal", 0) or 0
            tot_a = inv.get("amount", 0) or 0
            if not real_stocks and tot_a == 0 and tot_p == 0:
                continue
            tot_pnl_amt = tot_a - tot_p
            tot_pnl_pct = calc_pnl(tot_p, tot_a)
            pnl_sign = "+" if tot_pnl_amt > 0 else ""
            pnl_color = "#ef4444" if tot_pnl_amt > 0 else "#3b82f6" if tot_pnl_amt < 0 else "#64748b"

            if real_stocks and show_stocks:
                # 계좌 헤더 (읽기 전용)
                st.markdown(f'''
<div style="margin-bottom:0;background:#f8fafc;padding:14px 16px;border-radius:12px 12px 0 0;border:1px solid #e2e8f0;border-bottom:2px solid #cbd5e1;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <span style="font-size:1rem;font-weight:700;color:#0f172a;">🏦 {acc_type}</span>
    <span style="font-size:0.85rem;color:#64748b;">원금: {int(round(tot_p)):,}원</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:1rem;font-weight:700;color:#1e293b;">평가액: {int(round(tot_a)):,}원</span>
    <span style="font-size:0.9rem;font-weight:700;color:{pnl_color};">{pnl_sign}{int(round(tot_pnl_amt)):,}원 ({pnl_sign}{tot_pnl_pct:.1f}%)</span>
  </div>
</div>''', unsafe_allow_html=True)
                n_stocks = len(real_stocks)
                for i, s in enumerate(sorted(real_stocks, key=get_sort_key)):
                    sname  = s.get("stock_name", "")
                    qty    = s.get("quantity", 0) or 0
                    s_val  = s.get("valuation", 0) or 0
                    s_prin = s.get("principal", 0) or 0
                    s_pnl  = s_val - s_prin
                    s_pct  = calc_pnl(s_prin, s_val)
                    s_color = "#ef4444" if s_pnl > 0 else "#3b82f6" if s_pnl < 0 else "#64748b"
                    s_sign  = "+" if s_pnl > 0 else ""
                    qty_str = f"{qty:g}주" if qty else "-"
                    is_last = (i == n_stocks - 1)
                    br = "border-radius:0 0 12px 12px;" if is_last else ""
                    mb = "margin-bottom:12px;" if is_last else ""
                    st.markdown(f'''
<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:#ffffff;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;{br}{mb}">
  <div><span style="font-size:0.95rem;font-weight:600;color:#1e293b;">{sname}</span><br>
    <span style="font-size:0.78rem;color:#94a3b8;">{qty_str}</span></div>
  <div style="text-align:right;"><span style="font-size:0.95rem;font-weight:600;color:#1e293b;">{int(round(s_val)):,}원</span><br>
    <span style="font-size:0.78rem;font-weight:600;color:{s_color};">{s_sign}{int(round(s_pnl)):,} ({s_sign}{s_pct:.1f}%)</span></div>
</div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
<div style="margin-bottom:12px;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <span style="font-size:1rem;font-weight:700;color:#0f172a;">🏦 {acc_type}</span>
    <span style="font-size:0.85rem;color:#64748b;">원금: {int(round(tot_p)):,}원</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:1rem;font-weight:700;color:#1e293b;">평가액: {int(round(tot_a)):,}원</span>
    <span style="font-size:0.9rem;font-weight:700;color:{pnl_color};">{pnl_sign}{int(round(tot_pnl_amt)):,}원 ({pnl_sign}{tot_pnl_pct:.1f}%)</span>
  </div>
</div>''', unsafe_allow_html=True)

    _render_group("현금성 자산", "💰", cash_invs)
    _render_group("비현금성 자산", "🏠", non_cash_invs)

with tab_fam:
    _draw_pie_tab("가족 전체", total_data["tot_p"], cash_data["tot_p"], non_cash_data["tot_p"], is_total=True)
    draw_light_divider()
    st.subheader("\U0001f4cb 계좌별 현황 — 👨 준영")
    render_detail_table("준영", prefix="fam_jy_")
    draw_light_divider()
    st.subheader("\U0001f4cb 계좌별 현황 — \U0001f469 지윤")
    render_detail_table("지윤", prefix="fam_ji_")
with tab_jy:
    _draw_pie_tab("준영", total_data["jy_p"], cash_data["jy_p"], non_cash_data["jy_p"], is_total=False)
    draw_light_divider()
    st.subheader("\U0001f4cb 계좌별 상세 현황")
    render_detail_table("준영", prefix="tab_jy_")
with tab_ji:
    _draw_pie_tab("지윤", total_data["ji_p"], cash_data["ji_p"], non_cash_data["ji_p"], is_total=False)
    draw_light_divider()
    st.subheader("\U0001f4cb 계좌별 상세 현황")
    render_detail_table("지윤", prefix="tab_ji_")

draw_light_divider()



draw_light_divider()

# ── 자산 수정 ──────────────────────────────────────────────
st.subheader("✏️ 자산 수정")
st.caption("계좌를 선택하고 금액이나 종목을 수정한 뒤 저장하세요. 저장하면 위 현황에 즉시 반영됩니다.")

tab_jy_edit, tab_jd_edit = st.tabs(["👨 준영", "👩 지윤"])


def _si(v, d=0) -> int:
    """NaN/None 포함 안전하게 int 변환"""
    try:
        import math
        if v is None: return d
        f = float(v)
        if math.isnan(f) or math.isinf(f): return d
        return int(f)
    except: return d

def _sf(v, d=0.0) -> float:
    """NaN/None 포함 안전하게 float 변환"""
    try:
        import math
        if v is None: return d
        f = float(v)
        if math.isnan(f) or math.isinf(f): return d
        return f
    except: return d

def _render_stock_editor(owner: str, sel_acc: str):
    from utils.stock_price import get_current_price

    st.caption("평단가와 수량을 입력한 뒤 **🔄 현재가 일괄 조회** 버튼을 누르세요. 평가액과 손익이 자동으로 계산됩니다.")

    inv = next((i for i in invests if i["owner"] == owner and i["account_type"] == sel_acc), None)
    existing = [
        s for s in inv_stocks_map.get(inv["id"], [])
        if s.get("stock_name", "") not in SKIP_STOCK_NAMES
    ] if inv else []

    data_key   = f"sdata_{owner}_{sel_acc}"
    editor_key = f"sedit_{owner}_{sel_acc}"

    if data_key not in st.session_state or st.session_state.get(f"sdata_acc_{owner}") != sel_acc:
        st.session_state[f"sdata_acc_{owner}"] = sel_acc
        if existing:
            st.session_state[data_key] = [
                {
                    "종목명": s.get("stock_name", ""),
                    "수량": float(s.get("quantity", 0) or 0),
                    "평단가": int(s.get("average_price", 0) or 0),
                    "현재가": int(s.get("current_price", 0) or 0),
                    "원금": int(s.get("principal", 0) or 0),
                    "평가수익": int(s.get("valuation", 0) or 0) - int(s.get("principal", 0) or 0),
                    "평가액": int(s.get("valuation", 0) or 0),
                }
                for s in existing
            ]
        else:
            st.session_state[data_key] = [
                {"종목명": "", "수량": 0.0, "평단가": 0, "현재가": 0, "원금": 0, "평가수익": 0, "평가액": 0}
            ]
        if editor_key in st.session_state:
            del st.session_state[editor_key]

    import pandas as pd
    edited_df = st.data_editor(
        pd.DataFrame(st.session_state[data_key]),
        key=editor_key,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "종목명":  st.column_config.TextColumn("종목명 (이름/코드)", width="medium"),
            "수량":    st.column_config.NumberColumn("수량", min_value=0, step=0.1, format="%.2f"),
            "평단가":  st.column_config.NumberColumn("평단가(₩)", min_value=0, format="%d"),
            "현재가":  st.column_config.NumberColumn("현재가(₩)", min_value=0, format="%d"),
            "원금":    st.column_config.NumberColumn("원금(₩)", format="%d"),
            "평가수익": st.column_config.NumberColumn("평가수익(₩)", format="%d"),
            "평가액":  st.column_config.NumberColumn("평가액 (자동)", disabled=True, format="%d"),
        },
        disabled=["평가액"] if not is_closed else True,
    )

    col_a, col_b = st.columns(2)

    is_current_month = (year == datetime.now().year and month == datetime.now().month)
    fetch_disabled = is_closed or not is_current_month
    fetch_help = "현재가 일괄 조회는 '당월' 데이터에서만 가능합니다." if not is_current_month else None

    if col_a.button("🔄 현재가 일괄 조회", key=f"fetch_{owner}_{sel_acc}",
                    use_container_width=True, disabled=fetch_disabled, help=fetch_help):
        rows = edited_df.to_dict("records")
        prog = st.progress(0, text="조회 중...")
        names = [str(r.get("종목명", "")).strip() for r in rows]
        valid = [(i, n) for i, n in enumerate(names) if n]

        for step, (i, name) in enumerate(valid):
            prog.progress((step + 1) / max(len(valid), 1), text=f"🔍 {name} 조회 중...")
            row = rows[i].copy()
            info = get_current_price(name)
            if info:
                qty   = _sf(row.get("수량"))
                avg_p = _si(row.get("평단가"))
                price = info["price"]
                row["종목명"] = info["name"]
                row["현재가"] = price
                row["원금"]   = int(avg_p * qty)
                row["평가액"] = int(price * qty)
                row["평가수익"] = row["평가액"] - row["원금"]
            else:
                st.warning(f"⚠️ '{name}' 현재가 조회 실패 (종목명 확인 필요)")
            rows[i] = row

        prog.empty()
        st.session_state[data_key] = rows
        if editor_key in st.session_state:
            del st.session_state[editor_key]
        st.rerun()

    if col_b.button("💾 저장", key=f"save_stocks_{owner}_{sel_acc}",
                    use_container_width=True, disabled=is_closed):
        rows = edited_df.to_dict("records")
        stocks_to_save = []
        tot_p, tot_a = 0, 0

        for row in rows:
            name = str(row.get("종목명", "") or "").strip()
            if not name or name == "nan":
                continue
            qty   = _sf(row.get("수량"))
            avg_p = _si(row.get("평단가"))
            cur_p = _si(row.get("현재가"))
            prin  = _si(row.get("원금"))
            pnl   = _si(row.get("평가수익"))
            
            # 원금이 직접 입력되지 않았으면 수량*평단가
            if prin == 0 and qty > 0 and avg_p > 0:
                prin = int(qty * avg_p)
                
            # 평가액 계산 (수량*현재가 우선, 그다음 원금+평가수익)
            if cur_p > 0 and qty > 0:
                val = int(qty * cur_p)
            elif pnl != 0:
                val = prin + pnl
            else:
                val = prin
                
            tot_p += prin
            tot_a += val
            stocks_to_save.append({
                "stock_name": name, "quantity": qty,
                "average_price": avg_p, "current_price": cur_p,
                "principal": prin, "valuation": val,
            })

        if stocks_to_save:
            upsert_investment(year, month, owner, sel_acc, tot_p, tot_a)
            invs_after = get_investments(year, month)
            inv_id = next(
                (i["id"] for i in invs_after if i["owner"] == owner and i["account_type"] == sel_acc),
                None
            )
            if inv_id:
                replace_investment_stocks(inv_id, stocks_to_save)
            st.success(f"✅ {owner} / {sel_acc} 종목 데이터가 저장되었습니다! ({len(stocks_to_save)}개 종목)")
            st.session_state.pop(data_key, None)
            st.rerun()
        else:
            st.warning("저장할 종목이 없습니다.")


def _render_principal_editor(owner: str, sel_acc: str):
    """원금만 입력하는 계좌용 에디터 (CMA, 청년도약, 주택청약, IRP 등)"""
    inv = next((i for i in invests if i["owner"] == owner and i["account_type"] == sel_acc), None)
    tot_p = int(inv.get("principal", 0)) if inv else 0

    st.caption(f"**{sel_acc}** 계좌의 현재 납입(원금) 금액을 입력하세요.")
    new_p = st.number_input(
        "원금 (₩)", value=tot_p, step=10000,
        key=f"prin_{owner}_{sel_acc}", disabled=is_closed, format="%d"
    )
    if st.button("💾 저장", key=f"save_prin_{owner}_{sel_acc}",
                 use_container_width=True, type="primary", disabled=is_closed):
        upsert_investment(year, month, owner, sel_acc, new_p, new_p)
        st.success(f"✅ {owner} / {sel_acc} 원금이 {new_p:,}원으로 저장되었습니다!")
        st.rerun()


def render_edit_form(owner: str):
    sort_order = {"TOSS": 1, "중개형ISA": 2, "KB": 3, "총 예수금": 4,
                  "CMA": 5, "청년도약": 6, "주택청약": 7, "IRP": 8, "업비트": 9}
    owner_invs_sorted = sorted(
        [i for i in invests if i["owner"] == owner],
        key=lambda x: sort_order.get(x["account_type"], 99)
    )
    existing_accs = [i["account_type"] for i in owner_invs_sorted]

    all_possible = list(INVESTMENT_ACCOUNTS["현금성 자산"]) + list(INVESTMENT_ACCOUNTS["비현금성 자산"])
    if owner == "준영" and "업비트" in all_possible:
        all_possible.remove("업비트")

    # 기존 계좌 먼저, 이후 미사용 계좌
    display_accs = existing_accs + [a for a in all_possible if a not in existing_accs]

    sel_acc = st.selectbox("✏️ 수정할 계좌 선택", display_accs, key=f"edit_acc_{owner}")
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    if sel_acc in STOCK_INPUT_ACCOUNTS:
        _render_stock_editor(owner, sel_acc)
    else:
        _render_principal_editor(owner, sel_acc)


with tab_jy_edit:
    render_edit_form("준영")

with tab_jd_edit:
    render_edit_form("지윤")
