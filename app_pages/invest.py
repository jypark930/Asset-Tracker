"""
app_pages/invest.py  ─  투자현황
위: 전체 평가액·사람별/종류별 비중 → 가족·사람별 비교표 / 가운데: 보기(가족·준영·지윤)별 계좌 구성
아래: 자산 수정 (계좌 고르고 종목·원금 입력)
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.auth import get_current_user
from utils.currency import get_usd_krw_rate
from utils.db import (
    INVESTMENT_ACCOUNTS, get_investments, upsert_investment, get_monthly_income, upsert_monthly_income,
    get_all_investment_stocks, replace_investment_stocks, copy_previous_month_investments,
)
from utils.ui import page_header, now_kst, won, won_short, roll_number, flow_bar, legend_item, flash

CUSTOM_SORT_ORDER = [
    "Nh투자증권우", "NH투자증권우", "대신증권우", "LG화학우", "삼성화재우",
    "한국투자 ACE 고배당주증권 ETF", "ACE 고배당주", "현대차우", "KB금융", "BITO", "CONY",
    "코인베이스 글로벌", "코인베이스", "ETHU", "레드와이어", "Invesco QQQ Trust Series 1", "QQQ",
    "iShares Semiconductor ETF", "SOXX", "기업은행", "현대차2우B", "TIGER코스닥150", "코리안리",
    "서울보증보험", "우리금융지주", "KODEX미국배당커버드콜", "CJ우", "SK", "NAVER",
]
ACC_ORDER = {"TOSS": 1, "중개형ISA": 2, "KB": 3, "총 예수금": 4, "CMA": 5, "청년도약": 6,
             "주택청약": 7, "IRP": 8, "업비트": 9}
ACC_COLOR = {"TOSS": "#3b82f6", "KB": "#f59e0b", "총 예수금": "#10b981", "CMA": "#8b5cf6",
             "업비트": "#f43f5e", "청년도약": "#0ea5e9", "주택청약": "#60a5fa", "IRP": "#84cc16",
             "중개형ISA": "#ec4899"}
C_JY, C_JI = "#60a5fa", "#f472b6"
C_CASH, C_NONCASH = "#34d399", "#a78bfa"

now = now_kst()
year, month = page_header("투자현황")

# ── 마감 (지난 달만) ──────────────────────────────────────
is_past_month = (year, month) < (now.year, now.month)
inc = get_monthly_income(year, month)
confirmed_fields = (inc.get("confirmed_fields") or []) if inc else []  # NULL 도 빈 목록으로 (B13)
is_closed = "investments_closed" in confirmed_fields

if is_past_month:
    user = get_current_user()
    is_admin = user and user.email == "jypark930@naver.com"
    with st.container(horizontal=True, horizontal_alignment="center", vertical_alignment="center"):
        new_closed = st.toggle("이 달 마감", value=is_closed, disabled=is_closed and not is_admin,
                               key=f"close_toggle_{year}_{month}",
                               help="마감하면 이 달 자산을 고칠 수 없고, 대시보드 추이 그래프에 들어갑니다")
        st.markdown("<span class='at-badge ok'>마감됨</span>" if is_closed
                    else "<span class='at-badge warn'>아직 마감 안 함</span>", unsafe_allow_html=True)
    if new_closed != is_closed:
        if new_closed and "investments_closed" not in confirmed_fields:
            confirmed_fields.append("investments_closed")
        if not new_closed and "investments_closed" in confirmed_fields:
            confirmed_fields.remove("investments_closed")
        upsert_monthly_income(year, month, inc if inc else {}, confirmed_fields=confirmed_fields)
        st.rerun()

# ── 데이터 로드 및 집계 ─────────────────────────────────────
# 미래 달을 넘겨 보기만 해도 전월 계좌가 복사되던 문제(B4) 때문에 이번 달까지만 복사한다.
if (year, month) <= (now.year, now.month) and copy_previous_month_investments(year, month):
    st.toast("전월 투자 자산과 종목 내역을 복사해 왔습니다.", icon=":material/content_copy:")

invests = get_investments(year, month)
all_stocks = get_all_investment_stocks([i["id"] for i in invests])
inv_map = {(i["owner"], i["account_type"]): {"amount": i.get("amount", 0), "principal": i.get("principal", 0)}
           for i in invests}

# 계좌·종목 기준으로 묶기. 달러 예수금은 지금 환율로 원화 환산.
stock_map = {}
usd_rate = get_usd_krw_rate()
inv_by_id = {i["id"]: i for i in invests}
for s in all_stocks:
    inv = inv_by_id.get(s["investment_id"])
    if not inv:
        continue
    owner, acc, name = inv["owner"], inv["account_type"], s["stock_name"]
    qty, principal, valuation = s.get("quantity", 0), s.get("principal", 0), s.get("valuation", 0)
    if name == "예수금(현금)":
        name = "예수금(원화)"
    if acc == "총 예수금" and name == "예수금(달러)":
        valuation = principal = float(qty) * usd_rate
    d = stock_map.setdefault((acc, name), {"jy_p": 0, "jy_a": 0, "ji_p": 0, "ji_a": 0, "jy_qty": 0.0, "ji_qty": 0.0})
    pre = "jy" if owner == "준영" else "ji"
    d[f"{pre}_p"] += principal
    d[f"{pre}_a"] += valuation
    d[f"{pre}_qty"] += float(qty)

# 종목이 있는 계좌는 종목 합계로 계좌 금액을 덮어쓴다.
for owner, pre in (("준영", "jy"), ("지윤", "ji")):
    acc_sums = {}
    for (acc, name), d in stock_map.items():
        if d[f"{pre}_qty"] > 0 or d[f"{pre}_p"] > 0 or d[f"{pre}_a"] > 0:
            a = acc_sums.setdefault(acc, {"p": 0, "a": 0})
            a["p"] += d[f"{pre}_p"]
            a["a"] += d[f"{pre}_a"]
    for acc, sums in acc_sums.items():
        inv_map[(owner, acc)] = {"principal": sums["p"], "amount": sums["a"]}
        for i in invests:
            if i["owner"] == owner and i["account_type"] == acc:
                i["principal"], i["amount"] = sums["p"], sums["a"]


def calc_pnl(principal, amount):
    return 0.0 if not principal else (amount - principal) / principal * 100


cash_list = INVESTMENT_ACCOUNTS["현금성 자산"]
non_cash_list = INVESTMENT_ACCOUNTS["비현금성 자산"]


def _sum(owners, accs):
    p = sum(inv_map.get((o, a), {}).get("principal", 0) or 0 for o in owners for a in accs)
    a_ = sum(inv_map.get((o, a), {}).get("amount", 0) or 0 for o in owners for a in accs)
    return p, a_


ALL = cash_list + non_cash_list
OWNERS = {"가족": ["준영", "지윤"], "준영": ["준영"], "지윤": ["지윤"]}
tot_p, tot_a = _sum(["준영", "지윤"], ALL)


def _pnl_html(p, a, short=False) -> str:
    d = a - p
    if not p and not a:
        return "<span class='dim'>-</span>"
    cls = "up" if d > 0 else "down" if d < 0 else "dim"
    sign = "+" if d > 0 else "-" if d < 0 else ""
    amt = won_short(abs(d)) if short else f"{abs(int(round(d))):,}원"
    return f"<span class='{cls}'>{sign}{amt} ({sign}{abs(calc_pnl(p, a)):.1f}%)</span>"


def _pnl_md(p, a) -> str:
    d = a - p
    if not p:
        return ""
    color = "red" if d > 0 else "blue" if d < 0 else "gray"
    return f":{color}[{'+' if d > 0 else ''}{calc_pnl(p, a):.1f}%]"


# ── 한눈에 ───────────────────────────────────────────────
jy_p, jy_a = _sum(["준영"], ALL)
ji_p, ji_a = _sum(["지윤"], ALL)
cash_p, cash_a = _sum(["준영", "지윤"], cash_list)
nc_p, nc_a = _sum(["준영", "지윤"], non_cash_list)

if not invests:
    st.info(f"{year}년 {month}월에 등록된 투자 자산이 없습니다. 아래 '자산 수정'에서 계좌를 넣어 주세요.")
else:
    share = lambda v: f"{v / tot_a * 100:.0f}%" if tot_a else ""  # noqa: E731
    st.markdown(
        "<div class='at-kpi at-hero'>"
        "<div class='lbl'>가족 전체 평가액</div>"
        f"<div class='big'>{roll_number(won(tot_a))}</div>"
        f"<div class='sub at-table' style='display:block'>원금 <b>{won(tot_p)}</b> · 수익 {_pnl_html(tot_p, tot_a)}</div>"
        + flow_bar([("준영", jy_a, C_JY), ("지윤", ji_a, C_JI)], tot_a)
        + "<div class='at-legend'>"
        + legend_item("준영", won_short(jy_a), C_JY, share(jy_a))
        + legend_item("지윤", won_short(ji_a), C_JI, share(ji_a))
        + legend_item("현금성", won_short(cash_a), C_CASH, share(cash_a))
        + legend_item("비현금성", won_short(nc_a), C_NONCASH, share(nc_a))
        + "</div>"
        + flow_bar([("현금성", cash_a, C_CASH), ("비현금성", nc_a, C_NONCASH)], tot_a)
        + "</div>",
        unsafe_allow_html=True,
    )

    def _row(label, accs, sep=False):
        cells = ""
        for who in ("가족", "준영", "지윤"):
            p, a = _sum(OWNERS[who], accs)
            cells += f"<td>{won_short(a)}<br><span style='font-size:0.75rem'>{_pnl_html(p, a, short=True)}</span></td>"
        return f"<tr class='{'sep' if sep else ''}'><td>{label}</td>{cells}</tr>"

    def _prow(label, accs):
        return f"<tr><td>{label}</td>" + "".join(
            f"<td class='dim'>{won_short(_sum(OWNERS[w], accs)[0])}</td>" for w in ("가족", "준영", "지윤")) + "</tr>"

    with st.container(border=True, key="glass_inv_cmp"):
        st.markdown("**:material/group: 가족·사람별 비교** · 평가액 (아래 작은 글씨는 수익)")
        st.markdown(
            "<table class='at-table'><tr><th></th><th>가족</th><th>준영</th><th>지윤</th></tr>"
            + _row("전체", ALL) + _prow("　원금", ALL)
            + _row("현금성", cash_list, sep=True) + _prow("　원금", cash_list)
            + _row("비현금성", non_cash_list, sep=True) + _prow("　원금", non_cash_list)
            + "</table>",
            unsafe_allow_html=True,
        )

# ── 보기별 계좌 구성 ──────────────────────────────────────
inv_stocks_map = {}
for s in all_stocks:
    inv_stocks_map.setdefault(s["investment_id"], []).append(s)

SKIP_STOCK_NAMES = {"예수금(원화)", "예수금(달러)", "예수금(현금)", "예수금", "보유금액", "주택청약", "청년도약"}
STOCK_INPUT_ACCOUNTS = ["총 예수금", "중개형ISA", "IRP", "KB", "TOSS", "업비트"]  # 종목 입력 계좌
PRINCIPAL_ONLY_ACCOUNTS = ["총 예수금", "CMA", "청년도약"]


def _stock_sort_key(s):
    name = s.get("stock_name", "")
    return (0, CUSTOM_SORT_ORDER.index(name)) if name in CUSTOM_SORT_ORDER else (1, -(s.get("valuation", 0) or 0))


def _stock_rows(stocks) -> str:
    rows = ""
    for s in sorted(stocks, key=_stock_sort_key):
        qty = s.get("quantity", 0) or 0
        v, p = s.get("valuation", 0) or 0, s.get("principal", 0) or 0
        rows += (f"<tr><td>{s.get('stock_name', '')}<br><span class='dim' style='font-size:0.75rem'>"
                 f"{f'{qty:g}주' if qty else ''}</span></td>"
                 f"<td>{won(v)}<br><span style='font-size:0.75rem'>{_pnl_html(p, v)}</span></td></tr>")
    return f"<table class='at-table'><tr><th>종목</th><th>평가액 · 수익</th></tr>{rows}</table>"


if invests:
    st.markdown("#### :material/account_balance: 계좌 구성")
    view = st.segmented_control("보기", ["가족", "준영", "지윤"], default="가족", key="inv_view",
                                label_visibility="collapsed") or "가족"
    owners = OWNERS[view]
    accs = sorted({a for (o, a) in inv_map if o in owners}, key=lambda a: ACC_ORDER.get(a, 99))
    acc_vals = [(a, *_sum(owners, [a])) for a in accs]
    acc_vals = [x for x in acc_vals if x[1] or x[2]]

    c1, c2 = st.columns([2, 3], gap="medium")
    with c1, st.container(border=True, key="glass_inv_pie"):
        vp, va = _sum(owners, ALL)
        if not acc_vals:
            st.caption(f"{view} 자산이 없습니다.")
        else:
            fig = go.Figure(go.Pie(
                labels=[a for a, _, _ in acc_vals], values=[p for _, p, _ in acc_vals], sort=False,
                direction="clockwise", hole=0.62, textinfo="label", textposition="inside",
                insidetextorientation="horizontal",
                marker=dict(colors=[ACC_COLOR.get(a, "#94a3b8") for a, _, _ in acc_vals],
                            line=dict(color="rgba(26,25,28,0.9)", width=3)),
                hovertemplate="%{label}<br>원금 ₩%{value:,.0f} (%{percent})<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", font=dict(family="KoPub, sans-serif", color="#e5e7eb"),
                height=300, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                annotations=[dict(text=f"<b>{won_short(vp)}</b><br><span style='font-size:11px'>원금</span>",
                                  showarrow=False, font=dict(size=18, color="#f3f4f6"))],
            )
            st.plotly_chart(fig, config={"displayModeBar": False})
            st.caption(f"{view} 원금 기준 비중")

    with c2:
        for grp_name, grp_accs in (("현금성 자산", cash_list), ("비현금성 자산", non_cash_list)):
            rows = [x for x in acc_vals if x[0] in grp_accs]
            if not rows:
                continue
            gp, ga = _sum(owners, grp_accs)
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:4px 10px;justify-content:space-between;align-items:baseline;margin:6px 2px'>"
                        f"<b style='font-size:1.05rem;white-space:nowrap'>{grp_name}</b>"
                        f"<span class='at-table'>{won(ga)} · {_pnl_html(gp, ga, short=True)}</span></div>",
                        unsafe_allow_html=True)
            for acc, p, a in rows:
                label = f"**{acc}** · {won(a)} {_pnl_md(p, a)}"
                with st.expander(label):
                    if view == "가족":
                        lines = "".join(
                            f"<tr><td>{o}</td><td>{won(inv_map.get((o, acc), {}).get('amount', 0) or 0)}</td>"
                            f"<td class='dim'>{won(inv_map.get((o, acc), {}).get('principal', 0) or 0)}</td></tr>"
                            for o in ("준영", "지윤") if (o, acc) in inv_map)
                        st.markdown(f"<table class='at-table'><tr><th>사람</th><th>평가액</th><th>원금</th></tr>"
                                    f"{lines}</table>", unsafe_allow_html=True)
                    else:
                        inv = next((i for i in invests if i["owner"] == view and i["account_type"] == acc), None)
                        real = [s for s in inv_stocks_map.get(inv["id"], []) if s.get("stock_name", "") not in SKIP_STOCK_NAMES] if inv else []
                        st.markdown(f"<div class='at-table' style='margin-bottom:6px'>원금 {won(p)} · 수익 {_pnl_html(p, a)}</div>",
                                    unsafe_allow_html=True)
                        if real:
                            st.markdown(_stock_rows(real), unsafe_allow_html=True)



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

    st.caption("원금과 평가수익을 입력하고 저장해 주세요. 불필요한 내역을 삭제하려면 표 왼쪽 끝을 클릭해 행을 선택한 뒤, 키보드 Delete 키를 누르시거나 우측 상단의 휴지통 아이콘을 누르시면 됩니다.")

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
                    "원금": int(s.get("principal", 0) or 0),
                    "평가수익": int(s.get("valuation", 0) or 0) - int(s.get("principal", 0) or 0),
                    "평가액": int(s.get("valuation", 0) or 0),
                }
                for s in existing
            ]
        else:
            st.session_state[data_key] = [
                {"종목명": "", "원금": 0, "평가수익": 0, "평가액": 0}
            ]
        if editor_key in st.session_state:
            del st.session_state[editor_key]

    edited_df = st.data_editor(
        pd.DataFrame(st.session_state[data_key]),
        key=editor_key,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "종목명":  st.column_config.TextColumn("종목명 (계좌명 등)", width="medium"),
            "원금":    st.column_config.NumberColumn("원금 (원)", format="localized"),
            "평가수익": st.column_config.NumberColumn("평가수익 (원)", format="localized"),
            "평가액":  st.column_config.NumberColumn("평가액 (원, 자동)", disabled=True, format="localized"),
        },
        disabled=["평가액"] if not is_closed else True,
    )

    if st.button("💾 저장", key=f"save_stocks_{owner}_{sel_acc}", width="stretch", disabled=is_closed):
        rows = edited_df.to_dict("records")
        stocks_to_save = []
        tot_p, tot_a = 0, 0

        for row in rows:
            name = str(row.get("종목명", "") or "").strip()
            if not name or name == "nan":
                continue
            
            prin  = _si(row.get("원금"))
            pnl   = _si(row.get("평가수익"))
            val   = prin + pnl
            
            tot_p += prin
            tot_a += val
            stocks_to_save.append({
                "stock_name": name,
                "quantity": 0,
                "average_price": 0,
                "current_price": 0,
                "principal": prin,
                "valuation": val,
            })

        # B1: 화면에 안 보이는 행(예수금 등)은 그대로 보존하고 합계에도 넣는다.
        #     이름이 같고 금액이 그대로인 종목은 수량·평단·현재가를 유지한다.
        all_rows = inv_stocks_map.get(inv["id"], []) if inv else []
        hidden = [s for s in all_rows if s.get("stock_name", "") in SKIP_STOCK_NAMES]
        old_by_name = {s.get("stock_name", ""): s for s in all_rows
                       if s.get("stock_name", "") not in SKIP_STOCK_NAMES}
        for ns in stocks_to_save:
            os_ = old_by_name.get(ns["stock_name"])
            if os_ and int(os_.get("principal", 0) or 0) == ns["principal"]                     and int(os_.get("valuation", 0) or 0) == ns["valuation"]:
                for f in ("quantity", "average_price", "current_price"):
                    ns[f] = os_.get(f, 0) or 0
        for h in hidden:
            keep = {k: v for k, v in h.items()
                    if k not in ("id", "investment_id", "created_at", "updated_at")}
            stocks_to_save.append(keep)
            tot_p += int(h.get("principal", 0) or 0)
            tot_a += int(h.get("valuation", 0) or 0)

        if any(s["stock_name"] not in SKIP_STOCK_NAMES for s in stocks_to_save):
            upsert_investment(year, month, owner, sel_acc, tot_p, tot_a)
            invs_after = get_investments(year, month)
            inv_id = next(
                (i["id"] for i in invs_after if i["owner"] == owner and i["account_type"] == sel_acc),
                None
            )
            if inv_id:
                replace_investment_stocks(inv_id, stocks_to_save)
            flash(f"{owner} / {sel_acc} 종목 {len(stocks_to_save)}개를 저장했습니다.")
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
                 width="stretch", type="primary", disabled=is_closed):
        upsert_investment(year, month, owner, sel_acc, new_p, new_p)
        flash(f"{owner} / {sel_acc} 원금을 {new_p:,}원으로 저장했습니다.")
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



# ── 자산 수정 ─────────────────────────────────────────────
st.markdown("#### :material/edit: 자산 수정")
with st.container(border=True, key="glass_inv_edit"):
    if is_closed:
        st.caption(":material/lock: 마감한 달이라 고칠 수 없습니다. 고치려면 위에서 마감을 풀어 주세요.")
    else:
        st.caption("계좌를 고르고 금액이나 종목을 고친 뒤 저장하세요. 저장하면 위 현황에 바로 반영됩니다.")
    _view = st.session_state.get("inv_view")
    edit_owner = st.segmented_control("누구 자산", ["준영", "지윤"],
                                      default=_view if _view in ("준영", "지윤") else "준영",
                                      key="inv_edit_owner") or "준영"
    render_edit_form(edit_owner)
