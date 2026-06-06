"""
pages/3_📈_투자현황.py  ─  투자 자산 현황 관리
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="투자현황 | Asset Tracker", page_icon="📈", layout="wide")

from utils.auth import is_authenticated, try_restore_session, get_current_user
from utils.db import INVESTMENT_ACCOUNTS, get_investments, upsert_investment, get_monthly_income, upsert_monthly_income, get_all_investment_stocks, replace_investment_stocks

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("app.py")

now = datetime.now()
st.title("📈 투자 현황")

# ── 월 선택 ──────────────────────────────────────────────
cy, cm, c_close, _ = st.columns([1, 1, 2, 4])
with cy:
    year  = st.selectbox("연도", [2025, 2026, 2027], index=1, key="inv_year")
with cm:
    month = st.selectbox("월", list(range(1, 13)), index=now.month - 1, key="inv_month")

is_past_month = (year < now.year) or (year == now.year and month < now.month)
is_current_month = (year == now.year and month == now.month)
inc = get_monthly_income(year, month)
confirmed_fields = inc.get("confirmed_fields", []) if inc and "confirmed_fields" in inc else []
is_closed = "investments_closed" in confirmed_fields

with c_close:
    if is_past_month:
        user = get_current_user()
        is_admin = user and user.email == "jypark930@naver.com"
        
        # 마감이 Y일 때, 관리자가 아니면 변경 불가
        close_disabled = is_closed and not is_admin
        
        new_status = st.radio("마감 여부", ["Y", "N"], index=0 if is_closed else 1, horizontal=True, disabled=close_disabled, key="close_radio")
        
        if (new_status == "Y") != is_closed:
            if new_status == "Y":
                if "investments_closed" not in confirmed_fields:
                    confirmed_fields.append("investments_closed")
            else:
                if "investments_closed" in confirmed_fields:
                    confirmed_fields.remove("investments_closed")
            
            upsert_monthly_income(year, month, inc if inc else {}, confirmed_fields=confirmed_fields)
            st.rerun()

st.divider()

# ── 데이터 로드 및 집계 ───────────────────────────────────────────
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

# 총 예수금의 경우 하위 종목(현금, 달러)의 합계로 전체 계좌 데이터를 덮어씌움
for owner in ["준영", "지윤"]:
    p_key, a_key = ("jy_p", "jy_a") if owner == "준영" else ("ji_p", "ji_a")
    tot_p, tot_a = 0, 0
    has_stocks = False
    for (acc, name), d in stock_map.items():
        if acc == "총 예수금":
            has_stocks = True
            tot_p += d[p_key]
            tot_a += d[a_key]
    if has_stocks:
        inv_map[(owner, "총 예수금")] = {"principal": tot_p, "amount": tot_a}


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
        return f"{val:,}" if val != 0 else "-"
        
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

# ── 자산 구성 차트 ────────────────────────────────────────
st.subheader("🍰 총 자산 구성")
if invests and total_data["tot_a"] > 0:
    import plotly.graph_objects as go
    c1, c2 = st.columns(2, vertical_alignment="center")
    
    # 1. 총 자산 구성 (현금성 vs 비현금성)
    labels = ["현금성 자산", "비현금성 자산"]
    values = [cash_data["tot_a"], non_cash_data["tot_a"]]
    fig_tot = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.4,
        marker_colors=["#34d399", "#f87171"],
        textinfo="percent+label",
    ))
    fig_tot.update_layout(
        title="📊 전체 자산 평가액 구성",
        paper_bgcolor="rgba(0,0,0,0)", font_color="white",
        height=320, margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
    )
    with c1:
        st.plotly_chart(fig_tot, use_container_width=True)
        
    with c2:
        tot = total_data["tot_a"]
        st.markdown(f"## 💎 총 합계액: {tot:,}원")
        st.write("")
        st.markdown(f"### 💰 현금성 자산: {cash_data['tot_a']:,}원 ({cash_data['tot_a']/tot*100:.1f}%)")
        for acc in cash_list:
            d = get_row_data(acc)["tot_a"]
            if d > 0:
                st.write(f"- **{acc}**: {d/tot*100:.1f}% ({d:,}원)")
        st.write("")
        st.markdown(f"### 🏠 비현금성 자산: {non_cash_data['tot_a']:,}원 ({non_cash_data['tot_a']/tot*100:.1f}%)")
        for acc in non_cash_list:
            d = get_row_data(acc)["tot_a"]
            if d > 0:
                st.write(f"- **{acc}**: {d/tot*100:.1f}% ({d:,}원)")

    st.divider()

    # 2. 준영/지윤 개인 자산 구성
    c3, c4 = st.columns(2)
    def pie_for(owner):
        data = [(i["account_type"], i.get("amount", 0)) for i in invests if i["owner"] == owner and i.get("amount", 0) > 0]
        if not data:
            return None
        lbls, vals = zip(*data)
        fig = go.Figure(go.Pie(
            labels=lbls, values=vals,
            hole=0.4,
            marker_colors=["#a78bfa","#60a5fa","#34d399","#fb923c","#f87171","#fbbf24","#e879f9","#38bdf8"],
            textinfo="percent+label",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            height=320, margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
        )
        return fig

    with c3:
        st.markdown("### 👨 준영 자산 평가액 구성")
        jy_tot = total_data["jy_a"]
        if jy_tot > 0:
            st.markdown(f"**💎 총 자산:** {jy_tot:,}원")
            jy_cash_pct = cash_data["jy_a"] / jy_tot * 100
            jy_non_cash_pct = non_cash_data["jy_a"] / jy_tot * 100
            st.markdown(f"**💰 현금성:** {cash_data['jy_a']:,}원 ({jy_cash_pct:.1f}%) &nbsp;|&nbsp; **🏠 비현금성:** {non_cash_data['jy_a']:,}원 ({jy_non_cash_pct:.1f}%)")
        f = pie_for("준영")
        if f: st.plotly_chart(f, use_container_width=True)
        else: st.info("준영 자산 데이터 없음")
        
    with c4:
        st.markdown("### 👩 지윤 자산 평가액 구성")
        ji_tot = total_data["ji_a"]
        if ji_tot > 0:
            st.markdown(f"**💎 총 자산:** {ji_tot:,}원")
            ji_cash_pct = cash_data["ji_a"] / ji_tot * 100
            ji_non_cash_pct = non_cash_data["ji_a"] / ji_tot * 100
            st.markdown(f"**💰 현금성:** {cash_data['ji_a']:,}원 ({ji_cash_pct:.1f}%) &nbsp;|&nbsp; **🏠 비현금성:** {non_cash_data['ji_a']:,}원 ({ji_non_cash_pct:.1f}%)")
        f = pie_for("지윤")
        if f: st.plotly_chart(f, use_container_width=True)
        else: st.info("지윤 자산 데이터 없음")

st.divider()

st.write("")
st.write("")

# ── 통합 HTML 테이블 렌더링 ────────────────────────────────────

html_table = f"""
<style>
.inv-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: sans-serif;
    font-size: 14px;
}}
.inv-table th, .inv-table td {{
    border: 1px solid #444;
    padding: 8px;
}}
.inv-table th {{
    background-color: #333;
    text-align: center !important;
}}
.header-top th {{
    font-size: 16px;
}}
</style>
<table class="inv-table">
<thead>
<tr class="header-top">
<th rowspan="2" style="width: 15%;">자산 항목</th>
<th colspan="3" style="color: #fbbf24;">합계</th>
<th colspan="3" style="color: #60a5fa;">👨 준영 자산</th>
<th colspan="3" style="color: #f472b6;">👩 지윤 자산</th>
</tr>
<tr>
<th>원금</th><th>평가액</th><th>손익</th>
<th>원금</th><th>평가액</th><th>손익</th>
<th>원금</th><th>평가액</th><th>손익</th>
</tr>
</thead>
<tbody>
{build_tr("총 자산", total_data, is_bold=True, bg_color="#422006")}
{build_tr("현금성 자산", cash_data, is_bold=True, bg_color="#1e1b4b")}
"""

for acc in cash_list:
    html_table += build_tr(f"└ {acc} 계좌", get_row_data(acc), indent=1)
    # 당월인 경우에만 종목 표시 (또는 원할 경우 항상 표시)
    if is_current_month:
        stocks_in_acc = [name for (a, name) in stock_map.keys() if a == acc]
        for name in sorted(stocks_in_acc):
            d = stock_map[(acc, name)]
            jy_str = f"준:{d['jy_qty']}주" if d['jy_qty'] > 0 else ""
            ji_str = f"지:{d['ji_qty']}주" if d['ji_qty'] > 0 else ""
            qty_str = " / ".join(filter(None, [jy_str, ji_str]))
            label = f"▪ {name} ({qty_str})" if qty_str else f"▪ {name}"
            html_table += build_tr(label, get_stock_row_data(acc, name), indent=2, bg_color="#222")

html_table += build_tr("비현금성 자산", non_cash_data, is_bold=True, bg_color="#1e1b4b")

for acc in non_cash_list:
    html_table += build_tr(f"└ {acc} 계좌", get_row_data(acc), indent=1)
    if is_current_month:
        stocks_in_acc = [name for (a, name) in stock_map.keys() if a == acc]
        for name in sorted(stocks_in_acc):
            d = stock_map[(acc, name)]
            jy_str = f"준:{d['jy_qty']}주" if d['jy_qty'] > 0 else ""
            ji_str = f"지:{d['ji_qty']}주" if d['ji_qty'] > 0 else ""
            qty_str = " / ".join(filter(None, [jy_str, ji_str]))
            label = f"▪ {name} ({qty_str})" if qty_str else f"▪ {name}"
            html_table += build_tr(label, get_stock_row_data(acc, name), indent=2, bg_color="#222")

html_table += """</tbody>
</table>"""

st.markdown(html_table, unsafe_allow_html=True)
st.divider()

# ── 입력 폼 ──────────────────────────────────────────────
st.subheader("✏️ 자산 현황 업데이트")
st.caption("각 계좌의 원금과 현재 잔액(평가액)을 입력하거나, 📸 사진 업로드를 통해 종목별 자산을 자동 등록하세요.")

@st.dialog("📸 자동 매칭 통합 사진 업로드")
def open_bulk_upload_dialog(owner):
    st.write(f"**{owner}님의 카카오톡 캡처 사진**들을 한 번에 올려주세요.")
    st.caption("평가금액, 현재가 화면 등을 모두 선택해서 올려주시면 AI가 알아서 계좌를 식별하고 짝을 맞춰 분석합니다!")
    uploaded_files = st.file_uploader("사진 전체 선택", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if st.button("🔍 통합 분석 시작", disabled=not uploaded_files, use_container_width=True):
        with st.spinner("AI가 이미지들을 짝지어 계좌별로 분석 중입니다..."):
            import tempfile
            from utils.vision import analyze_kakao_assets
            
            f_paths = []
            for uf in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                    f.write(uf.getvalue())
                    f_paths.append(f.name)
            
            accounts_data = analyze_kakao_assets(f_paths)
            
            if accounts_data:
                st.success(f"분석 완료! {len(accounts_data)}개의 계좌 정보가 파악되었습니다.")
                st.json(accounts_data)
                
                # 각 계좌별로 DB 반영
                for acc_info in accounts_data:
                    acc_name = acc_info.get("account_name")
                    stocks = acc_info.get("stocks", [])
                    if not acc_name or not stocks:
                        continue
                        
                    tot_p = sum(s.get("principal", 0) for s in stocks)
                    tot_a = sum(s.get("valuation", 0) for s in stocks)
                    
                    upsert_investment(year, month, owner, acc_name, tot_p, tot_a)
                    invs_after = get_investments(year, month)
                    inv_id = next((i["id"] for i in invs_after if i["owner"] == owner and i["account_type"] == acc_name), None)
                    
                    if inv_id:
                        replace_investment_stocks(inv_id, stocks)
                
                st.success("데이터가 성공적으로 각 계좌에 자동 매칭되어 반영되었습니다!")
                st.rerun()
            else:
                st.error("분석에 실패했습니다. 사진을 다시 확인해주세요.")

tab_jy, tab_jd = st.tabs(["👨 준영 자산", "👩 지윤 자산"])

def render_investment_form(owner: str):
    if st.button(f"📸 {owner} 자산 자동 매칭 사진 업로드", key=f"btn_bulk_up_{owner}", disabled=is_closed, use_container_width=True):
        open_bulk_upload_dialog(owner)
        
    st.write("")
    c1, c2, c3 = st.columns([4, 3, 3])
    c2.caption("원금 (₩)")
    c3.caption("평가액 (₩)")
    
    all_accounts = INVESTMENT_ACCOUNTS["현금성 자산"] + INVESTMENT_ACCOUNTS["비현금성 자산"]
    for acc in all_accounts:
        if acc == "총 예수금":
            prefix = "jy_" if owner == "준영" else "ji_"
            cur_cash_a = stock_map.get(("총 예수금", "예수금(현금)"), {}).get(f"{prefix}a", 0)
            cur_usd_qty = stock_map.get(("총 예수금", "예수금(달러)"), {}).get(f"{prefix}qty", 0.0)
            
            c1, c2 = st.columns([4, 6])
            c1.markdown(f"<br>**{acc} (현금)**", unsafe_allow_html=True)
            c2.number_input(f"잔액 (₩)", 0, value=int(cur_cash_a), step=10000, key=f"inv_a_{owner}_{acc}_현금", disabled=is_closed, label_visibility="collapsed")
            
            c1, c2, c3 = st.columns([4, 3, 3])
            c1.markdown(f"<br>**{acc} (달러 USD)**", unsafe_allow_html=True)
            usd_key = f"inv_qty_{owner}_{acc}_달러"
            c2.number_input(f"달러 수량 ($)", 0.0, value=float(cur_usd_qty), step=10.0, key=usd_key, disabled=is_closed, label_visibility="collapsed")
            
            # 입력 중인 값을 실시간으로 반영하여 계산
            live_usd_qty = st.session_state.get(usd_key, cur_usd_qty)
            c3.markdown(f"<div style='margin-top:20px; color:#9ca3af;'>약 {int(live_usd_qty * usd_rate):,}원</div>", unsafe_allow_html=True)
        else:
            cur_p = inv_map.get((owner, acc), {}).get("principal", 0)
            cur_a = inv_map.get((owner, acc), {}).get("amount", 0)
            c1, c2, c3 = st.columns([4, 3, 3])
            c1.markdown(f"<br>**{acc}**", unsafe_allow_html=True)
            c2.number_input(f"원금 (₩)", 0, value=cur_p, step=10000, key=f"inv_p_{owner}_{acc}", disabled=is_closed, label_visibility="collapsed")
            c3.number_input(f"평가액 (₩)", 0, value=cur_a, step=10000, key=f"inv_a_{owner}_{acc}", disabled=is_closed, label_visibility="collapsed")
            
    if st.button(f"💾 {owner} 자산 수동 입력 전체 저장", key=f"save_btn_{owner}", disabled=is_closed, use_container_width=True):
        for acc in all_accounts:
            if acc == "총 예수금":
                cash_a = st.session_state[f"inv_a_{owner}_{acc}_현금"]
                cash_p = cash_a  # 현금은 원금과 평가액이 동일
                usd_qty = st.session_state[f"inv_qty_{owner}_{acc}_달러"]
                tot_p = cash_p + (usd_qty * usd_rate)
                tot_a = cash_a + (usd_qty * usd_rate)
                upsert_investment(year, month, owner, acc, int(tot_p), int(tot_a))
                
                invs_after = get_investments(year, month)
                inv_id = next((i["id"] for i in invs_after if i["owner"] == owner and i["account_type"] == acc), None)
                if inv_id:
                    stocks = [
                        {"stock_name": "예수금(현금)", "quantity": 1, "principal": cash_p, "valuation": cash_a},
                        {"stock_name": "예수금(달러)", "quantity": usd_qty, "principal": usd_qty * usd_rate, "valuation": usd_qty * usd_rate}
                    ]
                    replace_investment_stocks(inv_id, stocks)
            else:
                p_val = st.session_state[f"inv_p_{owner}_{acc}"]
                a_val = st.session_state[f"inv_a_{owner}_{acc}"]
                upsert_investment(year, month, owner, acc, p_val, a_val)
        st.success(f"✅ {owner} 자산 현황이 수동 저장되었습니다.")
        st.rerun()

with tab_jy:
    render_investment_form("준영")

with tab_jd:
    render_investment_form("지윤")
