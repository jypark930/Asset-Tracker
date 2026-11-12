"""
app_pages/ledger.py  ─  변동지출 입력·달력·내역·수정
"""
import calendar
import html
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.db import CATEGORIES, get_transactions, insert_transaction, update_transaction, delete_transaction
from utils.ui import page_header, now_kst, prev_of, won, won_short, flash, kpi_card, kpi_grid, delta_text

year, month = page_header("가계부")
today = now_kst()
txns = get_transactions(year, month)
max_day = calendar.monthrange(year, month)[1]
total = sum(t["amount"] for t in txns)


def _parse_amount(text: str) -> int:
    """'12,000' '12000원' '1.2만' '3만5천' 같은 입력을 숫자로"""
    t = (text or "").replace(",", "").replace("원", "").replace("₩", "").replace(" ", "")
    if not t:
        return 0
    try:
        if "만" in t or "천" in t:
            v = 0
            if "만" in t:
                a, t = t.split("만", 1)
                v += int(float(a or 1) * 10_000)
            if "천" in t:
                a, t = t.split("천", 1)
                v += int(float(a or 1) * 1_000)
            if t:
                v += int(t)
            return v
        return int(float(t))
    except ValueError:
        return 0


# ── 이번 달 요약 ─────────────────────────────────────────
days_passed = today.day if (year, month) == (today.year, today.month) else max_day
if (year, month) > (today.year, today.month):
    days_passed = 0
py, pm = prev_of(year, month)
prev_txns = get_transactions(py, pm)
same_day = days_passed if (year, month) == (today.year, today.month) else 31
prev_same = sum(t["amount"] for t in prev_txns if t["day"] <= same_day)
cmp_label = "지난달 같은 날까지" if (year, month) == (today.year, today.month) else "지난달 전체"
cd, cc = delta_text(total, prev_same)
cat_tot = {}
for t in txns:
    cat_tot[t["category"]] = cat_tot.get(t["category"], 0) + t["amount"]
top_cat = max(cat_tot.items(), key=lambda x: x[1]) if cat_tot else None
kpi_grid([
    kpi_card(f"{month}월 변동지출", won(total), f"{len(txns)}건", highlight=True),
    kpi_card("하루 평균", won(total // days_passed) if days_passed else "-",
             f"{days_passed}일 기준" if days_passed else ""),
    kpi_card(cmp_label, won(prev_same), cd.replace("전월 대비", "이번 달"), cc),
])

col_in, col_cal = st.columns([2, 3], gap="medium")

# ── 빠른 입력 ────────────────────────────────────────────
with col_in, st.container(border=True, key="glass_ledger_1", height="stretch"):
    st.markdown("#### :material/add_circle: 지출 입력")
    default_day = st.session_state.get(
        f"last_day_{year}_{month}",
        today.day if (year, month) == (today.year, today.month) else 1,
    )
    default_day = min(default_day, max_day)
    last_cat = st.session_state.get("last_cat", CATEGORIES[0])

    with st.form("add_tx_form", clear_on_submit=True, border=False):
        c1, c2 = st.columns([1, 3])
        f_day = c1.number_input("일", 1, max_day, default_day)
        f_amt_str = c2.text_input("금액", placeholder="예: 12,000 또는 1.2만")
        f_cat = st.pills("구분", CATEGORIES, default=last_cat if last_cat in CATEGORIES else CATEGORIES[0])
        f_desc = st.text_input("이용처", placeholder="예: 이마트")
        saved = st.form_submit_button("저장", type="primary", icon=":material/save:", width="stretch")

    if saved:
        f_amt = _parse_amount(f_amt_str)
        if f_amt <= 0:
            st.error("금액을 숫자로 입력하세요. 예: 12000, 12,000, 1.2만")
        elif not f_cat:
            st.error("구분을 하나 고르세요.")
        elif insert_transaction(year, month, int(f_day), f_amt, f_desc.strip(), f_cat):
            st.session_state[f"last_day_{year}_{month}"] = int(f_day)
            st.session_state["last_cat"] = f_cat
            flash(f"{int(f_day)}일 {f_cat} {won(f_amt)} 저장했습니다.")
            st.rerun()

# ── 달력 ────────────────────────────────────────────────
day_sum, day_items = {}, {}
for t in txns:
    d = t["day"]
    day_sum[d] = day_sum.get(d, 0) + t["amount"]
    day_items.setdefault(str(d), []).append({
        "desc": html.escape(t.get("description") or "-"),
        "cat": html.escape(t.get("category") or "-"),
        "amt": t["amount"],
    })

max_amt = max(day_sum.values() or [1])
cal = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
head = "".join(f'<th class="{"sun" if i == 0 else "sat" if i == 6 else ""}">{w}</th>'
               for i, w in enumerate(["일", "월", "화", "수", "목", "금", "토"]))
body = ""
for week in cal:
    row = ""
    for i, d in enumerate(week):
        if d == 0:
            row += '<td class="empty"></td>'
            continue
        cls = "today" if (year, month, d) == (today.year, today.month, today.day) else ""
        dcls = "sun" if i == 0 else "sat" if i == 6 else ""
        amt = day_sum.get(d, 0)
        amt_html = f'<span class="amt">{won_short(amt)}</span>' if amt else ""
        click = f' onclick="pop({d},event)"' if amt else ""
        has = " has" if amt else ""
        heat = f' style="background:rgba(59,130,246,{0.10 + 0.45 * amt / max_amt:.2f})"' if amt else ""
        row += f'<td class="{cls}{has}"{click}{heat}><span class="num {dcls}">{d}</span>{amt_html}</td>'
    body += f"<tr>{row}</tr>"

cal_html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:transparent;font-family:-apple-system,'Segoe UI',sans-serif}}
table{{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:3px}}
th{{color:#9ca3af;font-size:12px;font-weight:700;padding:4px 0}}
th.sun,.num.sun{{color:#f87171}} th.sat,.num.sat{{color:#3b82f6}}
td{{background:rgba(255,255,255,0.06);border-radius:10px;height:58px;vertical-align:top;padding:5px;border:1px solid rgba(255,255,255,0.08)}}
td.empty{{background:transparent;border:none}}
td.has{{cursor:pointer;background:rgba(59,130,246,0.14);border-color:rgba(96,165,250,0.40)}}
td.has:hover{{filter:brightness(1.25)}}
td.today{{outline:2px solid #3b82f6}}
.num{{display:block;font-size:12px;font-weight:700;color:#94a3b8}}
.amt{{display:block;margin-top:6px;font-size:12px;font-weight:800;color:#93c5fd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
#p{{display:none;position:fixed;z-index:9;background:#2a292e;border:1px solid rgba(255,255,255,0.12);border-radius:12px;
    box-shadow:0 10px 30px rgba(0,0,0,.18);padding:12px 14px;width:260px;max-height:300px;overflow:auto;font-size:13px}}
.t{{font-weight:800;margin-bottom:6px;color:#f1f5f9}}
.i{{display:flex;gap:6px;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05)}}
.c{{font-size:11px;color:#fff;background:#3b82f6;border-radius:4px;padding:1px 5px;white-space:nowrap}}
.d{{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#e2e8f0}}
.a{{font-weight:800;color:#f1f5f9;white-space:nowrap}}
.s{{text-align:right;font-weight:800;margin-top:6px;color:#93c5fd}}
</style></head><body><div id='p'></div><table><tr>{head}</tr>{body}</table><script>
var D={json.dumps(day_items, ensure_ascii=False)};
function pop(day,e){{e.stopPropagation();var d=D[String(day)],p=document.getElementById('p');if(!d)return;
var h='<div class="t">'+day+'일 지출</div>',s=0;d.forEach(function(x){{s+=x.amt;
h+='<div class="i"><span class="c">'+x.cat+'</span><span class="d">'+x.desc+'</span><span class="a">₩'+x.amt.toLocaleString('ko-KR')+'</span></div>';}});
h+='<div class="s">합계 ₩'+s.toLocaleString('ko-KR')+'</div>';p.innerHTML=h;
var r=e.currentTarget.getBoundingClientRect(),x=Math.min(r.left,window.innerWidth-270),y=r.bottom+4;
if(y+300>window.innerHeight)y=Math.max(4,r.top-304);p.style.left=Math.max(4,x)+'px';p.style.top=y+'px';p.style.display='block';}}
document.addEventListener('click',function(){{document.getElementById('p').style.display='none';}});
</script></body></html>"""

with col_cal, st.container(border=True, key="glass_ledger_2", height="stretch"):
    st.markdown("#### :material/calendar_month: 달력")
    st.caption("색이 진할수록 많이 쓴 날 · 누르면 내역이 보여요" + (f" · 가장 많이 쓴 곳: {top_cat[0]} {won_short(top_cat[1])}" if top_cat else ""))
    components.html(cal_html, height=len(cal) * 64 + 40, scrolling=False)


# ── 내역 / 수정 ──────────────────────────────────────────
@st.dialog("선택한 내역 삭제")
def _confirm_delete(ids: list, summary: str):
    st.write(f"**{len(ids)}건**을 삭제할까요? 되돌릴 수 없습니다.")
    st.caption(summary)
    c1, c2 = st.columns(2)
    if c1.button("삭제", type="primary", width="stretch", icon=":material/delete:"):
        ok = sum(delete_transaction(i) for i in ids)
        flash(f"{ok}건 삭제했습니다.", ":material/delete:")
        st.rerun()
    if c2.button("취소", width="stretch"):
        st.rerun()


st.markdown("#### :material/list_alt: 내역")
if not txns:
    st.caption(f"{year}년 {month}월 변동지출 내역이 없습니다.")
else:
    tab_list, tab_edit = st.tabs([f"목록 ({len(txns)}건)", "수정·삭제"])

    with tab_list:
        opts = ["전체"] + [c for c, _ in sorted(cat_tot.items(), key=lambda x: -x[1])]
        sel = st.pills("카테고리", opts, default="전체", key=f"cat_filter_{year}_{month}",
                       format_func=lambda c: c if c == "전체" else f"{c} {won_short(cat_tot[c])}",
                       label_visibility="collapsed")
        df = pd.DataFrame(txns)[["day", "category", "description", "amount"]]
        if sel and sel != "전체":
            df = df[df["category"] == sel]
        st.dataframe(
            df.sort_values(["day"], ascending=False),
            hide_index=True,
            column_config={
                "day": st.column_config.NumberColumn("일", width="small", format="%d일", alignment="left"),
                "category": st.column_config.TextColumn("구분"),
                "description": st.column_config.TextColumn("이용처"),
                "amount": st.column_config.NumberColumn("금액 (원)", format="localized"),
            },
        )
        st.caption(f"{len(df)}건 · 합계 {won(int(df['amount'].sum()))}")

    with tab_edit:
        st.caption("칸을 눌러 고친 뒤 '수정 저장'. 지우려면 맨 앞 칸을 체크하세요.")
        base = pd.DataFrame(txns)
        df_edit = base[["id", "day", "amount", "description", "category"]].copy()
        df_edit.insert(0, "삭제", False)
        edited = st.data_editor(
            df_edit,
            column_config={
                "삭제": st.column_config.CheckboxColumn("삭제", width="small"),
                "id": None,
                "day": st.column_config.NumberColumn("일", min_value=1, max_value=max_day, width="small", alignment="left"),
                "amount": st.column_config.NumberColumn("금액 (원)", min_value=0, format="localized"),
                "description": st.column_config.TextColumn("이용처"),
                "category": st.column_config.SelectboxColumn("구분", options=CATEGORIES),
            },
            hide_index=True,
            key=f"tx_editor_{year}_{month}",
        )

        orig = base.set_index("id")

        def _i(v) -> int:
            return 0 if v is None or pd.isna(v) else int(v)

        def _t(v) -> str:
            return "" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v)

        changes = []
        for _, row in edited.iterrows():
            if row["삭제"]:
                continue
            o = orig.loc[row["id"]]
            diff = {}
            if _i(row["day"]) != _i(o["day"]) and _i(row["day"]) >= 1:
                diff["day"] = _i(row["day"])
            if _i(row["amount"]) != _i(o["amount"]):
                diff["amount"] = _i(row["amount"])
            if _t(row["description"]) != _t(o["description"]):
                diff["description"] = _t(row["description"])
            if row["category"] != o["category"]:
                diff["category"] = row["category"]
            if diff:
                changes.append((row["id"], diff))
        to_del = edited[edited["삭제"]]

        with st.container(horizontal=True):
            if st.button(f"수정 저장 ({len(changes)}건)", type="primary", icon=":material/save:",
                         disabled=not changes):
                ok = sum(update_transaction(i, d) for i, d in changes)
                flash(f"{ok}건 수정했습니다.")
                st.rerun()
            if st.button(f"선택 삭제 ({len(to_del)}건)", icon=":material/delete:", disabled=to_del.empty):
                summary = ", ".join(f"{int(r.day)}일 {r.description or r.category} {won(r.amount)}"
                                    for r in to_del.itertuples())
                _confirm_delete(to_del["id"].tolist(), summary)
