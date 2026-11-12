"""
app_pages/finance.py  ─  재무현황: 수입이 고정비·생활비를 거쳐 '투자 가능 금액'이 되기까지
위: 요약 숫자 + 흐름 그래프 / 아래: 수입·고정비·생활비 탭 (표에서 바로 고치고 확정)
입력 안 한 항목은 전월 값을 '예상'으로 보여 준다 (이번 달 값이 있으면 그 값, B3).
"""
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.auth import EMAIL_TO_NAME
from utils.db import (
    get_monthly_income, upsert_monthly_income,
    get_fixed_costs, upsert_fixed_costs,
    get_utility_costs, upsert_utility_costs,
    get_transactions, get_other_incomes, insert_transaction, delete_transaction,
)
from utils.fin import (
    INCOME_ITEMS, FIXED_TREE, UTILITY_ITEMS, VARIABLE_GROUPS,
    INCOME_FIELDS, FIXED_FIELDS, UTILITY_FIELDS, merge_month,
)
from utils.ui import page_header, prev_of, won, won_short, kpi_card, kpi_grid, flash

year, month = page_header("재무현황", "표에서 금액을 고치고 '확정'을 체크한 뒤 저장하세요 · 체크 안 된 값은 전월 값으로 채운 예상치예요")
py, pm = prev_of(year, month)

# ── 데이터 ───────────────────────────────────────────────
inc_raw, fixed_raw, util_raw = get_monthly_income(year, month), get_fixed_costs(year, month), get_utility_costs(year, month)
inc, inc_cf = merge_month(inc_raw, get_monthly_income(py, pm))
fixed, fixed_cf = merge_month(fixed_raw, get_fixed_costs(py, pm))
util, util_cf = merge_month(util_raw, get_utility_costs(py, pm))
txns = get_transactions(year, month)
other_incomes = get_other_incomes(year, month)


def g(d: dict, k: str) -> int:
    return int(d.get(k, 0) or 0)


other_inc = sum(int(i.get("amount", 0) or 0) for i in other_incomes)
total_income = sum(g(inc, f) for f in INCOME_FIELDS) + other_inc
group_tot = {grp: sum(g(fixed, f) for _, f in items) for grp, items in FIXED_TREE}
total_fixed = sum(group_tot.values())
livable = total_income - total_fixed

total_utility = sum(g(util, f) for f in UTILITY_FIELDS)
cat_sum = {}
for t in txns:
    cat_sum[t.get("category", "기타")] = cat_sum.get(t.get("category", "기타"), 0) + int(t.get("amount", 0) or 0)
var_groups = [(name, [(c, cat_sum.get(c, 0)) for c in cats]) for name, cats in VARIABLE_GROUPS]
var_group_tot = {name: sum(v for _, v in items) for name, items in var_groups}
total_variable = total_utility + sum(var_group_tot.values())
investable = livable - total_variable

# ── 요약 ─────────────────────────────────────────────────
pct = (lambda v: f"수입의 {v / total_income * 100:.0f}%") if total_income else (lambda v: "")
kpi_grid([
    kpi_card("총 수입", won(total_income), f"기타 수입 {won_short(other_inc)} 포함" if other_inc else ""),
    kpi_card("고정비", won(total_fixed), pct(total_fixed)),
    kpi_card("생활 가능 금액", won(livable), "수입 − 고정비"),
    kpi_card("변동비", won(total_variable), pct(total_variable)),
    kpi_card("익월 투자 가능", won(investable), pct(investable) if investable > 0 else "생활 가능 − 변동비",
             "good" if investable >= 0 else "bad", highlight=True),
    kpi_card("투자 가능 비율", f"{investable / total_income * 100:.1f}%" if total_income else "-",
             "높을수록 좋아요"),
])

with st.container(border=True, key="glass_fin_flow"):
    st.markdown("**:material/waterfall_chart: 이번 달 돈의 흐름**")
    _short = {"생활지출": "생활<br>지출", "경조/선물비": "경조<br>선물"}  # 폰에서 글자 겹침 방지
    labels = ["수입", "고정비", "공과금"] + [_short.get(n, n) for n, _ in var_groups] + ["투자<br>가능"]
    vals = [total_income, -total_fixed, -total_utility] + [-var_group_tot[n] for n, _ in var_groups] + [investable]
    measure = ["absolute"] + ["relative"] * (len(labels) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=labels, y=vals, measure=measure,
        text=[won_short(abs(v)) for v in vals], textposition="outside",
        textfont=dict(color="#e5e7eb", size=12),
        connector=dict(line=dict(color="rgba(255,255,255,0.18)", width=1, dash="dot")),
        increasing=dict(marker=dict(color="#34d399")),
        decreasing=dict(marker=dict(color="#f472b6")),
        totals=dict(marker=dict(color="#60a5fa")),
        hovertemplate="₩%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300,
        font=dict(family="KoPub, sans-serif", color="#9ca3af"), showlegend=False,
        margin=dict(l=8, r=8, t=24, b=8),
        xaxis=dict(fixedrange=True, tickangle=0, tickfont=dict(size=11)),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickformat=",.0f",
                   showticklabels=False),
        hoverlabel=dict(bgcolor="#2a292e", font=dict(color="#f3f4f6")),
    )
    if total_income or total_fixed or total_variable:
        st.plotly_chart(fig, config={"displayModeBar": False})
    else:
        st.caption("아직 값이 없습니다.")


# ── 공통: 표로 고치기 ─────────────────────────────────────
def _who_when(raw: dict) -> str:
    by, at = (raw or {}).get("updated_by") or "", (raw or {}).get("updated_at") or ""
    if not by or not at:
        return ""
    try:
        when = (datetime.fromisoformat(at.replace("Z", "+00:00")) + timedelta(hours=9)).strftime("%m/%d %H:%M")
    except ValueError:
        when = at[:10]
    return f"마지막 수정: {EMAIL_TO_NAME.get(by, by)} · {when}"


def section_editor(key: str, rows: list[dict], data: dict, cf: list, fields: list, upsert_fn, raw: dict,
                   extra_cols: dict | None = None):
    """rows: [{..., '항목', '금액', '확정', '_f'}] → 표에서 고치고 저장. cf 의 다른 표시(마감 등)는 그대로 둔다."""
    df = pd.DataFrame(rows)
    n_unc = int((~df["확정"]).sum())
    badge = (f"<span class='at-badge warn'>예상 {n_unc}개</span>" if n_unc
             else "<span class='at-badge ok'>모두 확정</span>")
    st.markdown(badge, unsafe_allow_html=True)
    cols = {"_f": None,
            "항목": st.column_config.TextColumn("항목", disabled=True),
            "금액": st.column_config.NumberColumn("금액 (원)", min_value=0, step=1000, format="localized"),
            "확정": st.column_config.CheckboxColumn("확정", width="small")}
    cols.update(extra_cols or {})
    edited = st.data_editor(df, key=f"fin_{key}_{year}_{month}", hide_index=True, column_config=cols,
                            num_rows="fixed", height=40 + 35 * len(df))

    def _amt(v) -> int:
        return 0 if v is None or pd.isna(v) else int(v)

    changed = [r for r, o in zip(edited.to_dict("records"), rows)
               if _amt(r["금액"]) != o["금액"] or bool(r["확정"]) != o["확정"]]

    def _save(confirm_all: bool):
        new = dict(data)
        recs = edited.to_dict("records")
        for r in recs:
            new[r["_f"]] = _amt(r["금액"])
        keep = [x for x in cf if x not in fields]
        new_cf = keep + [r["_f"] for r in recs if confirm_all or r["확정"]]
        if upsert_fn(year, month, new, new_cf):
            flash("저장했습니다." if not confirm_all else "모두 확정했습니다.")
            st.rerun()

    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button(f"저장 ({len(changed)}건)", key=f"fin_save_{key}", type="primary",
                     icon=":material/save:", disabled=not changed):
            _save(False)
        if st.button("전부 확정", key=f"fin_conf_{key}", icon=":material/done_all:", disabled=not n_unc,
                     help="표에 보이는 금액 그대로 모두 확정합니다"):
            _save(True)
        st.caption(_who_when(raw))


def cat_rows(items: list[tuple[str, int]], top: int) -> str:
    top = top or 1
    return "".join(
        f"<div class='at-cat'><div class='name'>{n}</div>"
        f"<div class='track'><div style='width:{v / top * 100:.1f}%'></div></div>"
        f"<div class='amt'>{won(v)}</div></div>"
        for n, v in items
    )


# ── 탭 ──────────────────────────────────────────────────
tab_inc, tab_fix, tab_var = st.tabs([
    f":material/payments: 수입 {won_short(total_income)}",
    f":material/lock: 고정비 {won_short(total_fixed)}",
    f":material/shopping_cart: 생활비 {won_short(total_variable)}",
])

with tab_inc:
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1, st.container(border=True, key="glass_fin_inc"):
        st.markdown("**급여·상여**")
        section_editor(
            "income",
            [{"사람": p, "항목": n, "금액": g(inc, f), "확정": f in inc_cf, "_f": f} for p, n, f in INCOME_ITEMS],
            inc, inc_cf, INCOME_FIELDS, upsert_monthly_income, inc_raw,
            {"사람": st.column_config.TextColumn("사람", disabled=True, width="small")},
        )
    with c2, st.container(border=True, key="glass_fin_other"):
        st.markdown(f"**기타 수입** · {won(other_inc)}")
        if not other_incomes:
            st.caption("등록된 기타 수입이 없습니다.")
        for oi in other_incomes:
            r1, r2, r3 = st.columns([5, 4, 1.4], vertical_alignment="center")
            r1.markdown(oi.get("description") or "-")
            r2.markdown(f"**{won(oi.get('amount', 0))}**")
            if r3.button("", key=f"del_other_{oi['id']}", icon=":material/delete:", help="삭제"):
                delete_transaction(oi["id"])
                flash("기타 수입을 삭제했습니다.", ":material/delete:")
                st.rerun()
        with st.form("add_other_inc_form", clear_on_submit=True, border=False):
            a1, a2 = st.columns([3, 2])
            new_desc = a1.text_input("내용", placeholder="예: 당근마켓 판매")
            new_amt = a2.number_input("금액 (원)", min_value=0, step=1000)
            if st.form_submit_button("추가", icon=":material/add:", width="stretch"):
                if not new_desc:
                    st.error("내용을 입력해주세요.")
                elif new_amt <= 0:
                    st.error("금액을 0원보다 크게 입력해주세요.")
                elif insert_transaction(year, month, 1, int(new_amt), new_desc, "기타 수입"):
                    flash(f"기타 수입 {won(new_amt)} 추가했습니다.")
                    st.rerun()

with tab_fix:
    c1, c2 = st.columns([2, 3], gap="medium")
    with c1, st.container(border=True, key="glass_fin_fixgrp"):
        st.markdown("**분류별 합계**")
        grp_items = sorted(group_tot.items(), key=lambda x: -x[1])
        st.markdown(cat_rows(grp_items, grp_items[0][1] if grp_items else 0), unsafe_allow_html=True)
        st.caption(f"합계 {won(total_fixed)}")
    with c2, st.container(border=True, key="glass_fin_fix"):
        st.markdown("**항목별 금액**")
        section_editor(
            "fixed",
            [{"분류": grp, "항목": n, "금액": g(fixed, f), "확정": f in fixed_cf, "_f": f}
             for grp, items in FIXED_TREE for n, f in items],
            fixed, fixed_cf, FIXED_FIELDS, upsert_fixed_costs, fixed_raw,
            {"분류": st.column_config.TextColumn("분류", disabled=True, width="small")},
        )

with tab_var:
    c1, c2 = st.columns([2, 3], gap="medium")
    with c1, st.container(border=True, key="glass_fin_util"):
        st.markdown(f"**공과금** · {won(total_utility)}")
        section_editor(
            "utility",
            [{"항목": n, "금액": g(util, f), "확정": f in util_cf, "_f": f} for n, f in UTILITY_ITEMS],
            util, util_cf, UTILITY_FIELDS, upsert_utility_costs, util_raw,
        )
    with c2, st.container(border=True, key="glass_fin_auto"):
        st.markdown("**가계부에서 자동으로 모은 금액**")
        top = max([v for _, items in var_groups for _, v in items] + [1])
        for name, items in var_groups:
            st.markdown(f"<div style='margin-top:10px;font-weight:800;color:#e5e7eb'>{name} "
                        f"<span style='color:#93c5fd'>{won(var_group_tot[name])}</span></div>"
                        + cat_rows(items, top), unsafe_allow_html=True)
        st.page_link("app_pages/ledger.py", label="가계부에서 고치기", icon=":material/receipt_long:")
