"""
투자현황 페이지 UI 개편 스크립트
- render_detail_table: 수정버튼 제거, 읽기전용 깔끔한 카드
- 하단 편집 섹션: 가계부 스타일(계좌 선택 → 테이블 수정 → 저장)
"""

file_path = "pages/4_📈_투자현황.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ────────────────────────────────────────────────────────────
# 1) render_detail_table 함수 + 탭 렌더링 전체 교체
#    (marker: "def render_detail_table" ... "draw_light_divider()\n\n\n\n\n\ndraw_light_divider()")
# ────────────────────────────────────────────────────────────

OLD_SECTION_A = '''def render_detail_table(owner_key, prefix="", show_stocks=True):
    owner_invs = [i for i in invests if i["owner"] == owner_key]
    if not owner_invs:
        st.info(f"{owner_key}님의 등록된 자산이 없습니다.")
        return

    # 사용자 지정 계좌 정렬 순서
    sort_order = {
        "TOSS": 1,
        "중개형ISA": 2,
        "KB": 3,
        "총 예수금": 4,
        "CMA": 5,
        "청년도약": 6,
        "주택청약": 7,
        "IRP": 8
    }
    owner_invs.sort(key=lambda x: sort_order.get(x["account_type"], 99))

    cash_invs = [i for i in owner_invs if i["account_type"] in INVESTMENT_ACCOUNTS["현금성 자산"]]
    non_cash_invs = [i for i in owner_invs if i["account_type"] not in INVESTMENT_ACCOUNTS["현금성 자산"]]

    def _render_group(title, icon, invs, prefix="", show_stocks=True):'''

# 찾기
if OLD_SECTION_A not in content:
    print("ERROR: OLD_SECTION_A not found!")
    exit(1)
print("OLD_SECTION_A found OK")

# 종료 마커: 탭 렌더링 끝 부분
OLD_END_A = '''draw_light_divider()




'''

# OLD_SECTION_A 이후에서 OLD_END_A 찾기
start_idx = content.index(OLD_SECTION_A)
# 탭 렌더링 블록 끝 마커
TAB_END_MARKER = '''draw_light_divider()




'''
# 탭 렌더링 끝을 render_detail_table 이후에서 찾기
search_from = start_idx
end_idx = content.index(TAB_END_MARKER, search_from)
end_idx_full = end_idx + len(TAB_END_MARKER)

OLD_BLOCK_A = content[start_idx:end_idx_full]

NEW_BLOCK_A = '''def render_detail_table(owner_key, prefix=""):
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

            if real_stocks:
                # 계좌 헤더 (읽기 전용)
                st.markdown(f\'\'\'
<div style="margin-bottom:0;background:#f8fafc;padding:14px 16px;border-radius:12px 12px 0 0;border:1px solid #e2e8f0;border-bottom:2px solid #cbd5e1;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <span style="font-size:1rem;font-weight:700;color:#0f172a;">🏦 {acc_type}</span>
    <span style="font-size:0.85rem;color:#64748b;">원금: {int(round(tot_p)):,}원</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:1rem;font-weight:700;color:#1e293b;">평가액: {int(round(tot_a)):,}원</span>
    <span style="font-size:0.9rem;font-weight:700;color:{pnl_color};">{pnl_sign}{int(round(tot_pnl_amt)):,}원 ({pnl_sign}{tot_pnl_pct:.1f}%)</span>
  </div>
</div>\'\'\', unsafe_allow_html=True)
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
                    st.markdown(f\'\'\'
<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:#ffffff;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;{br}{mb}">
  <div><span style="font-size:0.95rem;font-weight:600;color:#1e293b;">{sname}</span><br>
    <span style="font-size:0.78rem;color:#94a3b8;">{qty_str}</span></div>
  <div style="text-align:right;"><span style="font-size:0.95rem;font-weight:600;color:#1e293b;">{int(round(s_val)):,}원</span><br>
    <span style="font-size:0.78rem;font-weight:600;color:{s_color};">{s_sign}{int(round(s_pnl)):,} ({s_sign}{s_pct:.1f}%)</span></div>
</div>\'\'\', unsafe_allow_html=True)
            else:
                st.markdown(f\'\'\'
<div style="margin-bottom:10px;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;">
  <span style="font-size:1rem;font-weight:700;color:#0f172a;">🏦 {acc_type}</span>
  <div style="text-align:right;">
    <span style="font-size:1rem;font-weight:700;color:#1e293b;">원금: {int(round(tot_p)):,}원</span>
    <span style="font-size:0.85rem;font-weight:600;color:{pnl_color};margin-left:8px;">{pnl_sign}{int(round(tot_pnl_amt)):,}원</span>
  </div>
</div>\'\'\', unsafe_allow_html=True)

    _render_group("현금성 자산 원금", "💰", cash_invs)
    _render_group("비현금성 자산 원금", "🏠", non_cash_invs)

with tab_fam:
    _draw_pie_tab("가족 전체", total_data["tot_p"], cash_data["tot_p"], non_cash_data["tot_p"], is_total=True)
    draw_light_divider()
    st.subheader("\\U0001f4cb 계좌별 현황 — 👨 준영")
    render_detail_table("준영", prefix="fam_jy_")
    draw_light_divider()
    st.subheader("\\U0001f4cb 계좌별 현황 — \\U0001f469 지윤")
    render_detail_table("지윤", prefix="fam_ji_")
with tab_jy:
    _draw_pie_tab("준영", total_data["jy_p"], cash_data["jy_p"], non_cash_data["jy_p"], is_total=False)
    draw_light_divider()
    st.subheader("\\U0001f4cb 계좌별 상세 현황")
    render_detail_table("준영", prefix="tab_jy_")
with tab_ji:
    _draw_pie_tab("지윤", total_data["ji_p"], cash_data["ji_p"], non_cash_data["ji_p"], is_total=False)
    draw_light_divider()
    st.subheader("\\U0001f4cb 계좌별 상세 현황")
    render_detail_table("지윤", prefix="tab_ji_")

draw_light_divider()


'''

content = content[:start_idx] + NEW_BLOCK_A + content[end_idx_full:]
print("Block A replaced OK")

# ────────────────────────────────────────────────────────────
# 2) 하단 편집 섹션 전체 교체
#    (marker: "draw_light_divider()\n\n# ── 종목 추가..." ... 파일 끝)
# ────────────────────────────────────────────────────────────

OLD_BOTTOM_MARKER = '''draw_light_divider()

# ── 종목 추가 및 일괄 편집 ──────────────────────────────────
st.subheader("➕ 신규 종목 추가 및 일괄 편집")'''

if OLD_BOTTOM_MARKER not in content:
    print("ERROR: OLD_BOTTOM_MARKER not found!")
    exit(1)

bot_start = content.index(OLD_BOTTOM_MARKER)
# 파일 끝까지 교체
OLD_BOTTOM_BLOCK = content[bot_start:]

NEW_BOTTOM_BLOCK = '''draw_light_divider()

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
                    "평가액": int(s.get("valuation", 0) or 0),
                }
                for s in existing
            ]
        else:
            st.session_state[data_key] = [
                {"종목명": "", "수량": 0.0, "평단가": 0, "현재가": 0, "원금": 0, "평가액": 0}
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
            "종목명":  st.column_config.TextColumn("종목명 (이름 or 6자리 코드)", width="medium"),
            "수량":    st.column_config.NumberColumn("수량", min_value=0, step=0.1, format="%.2f"),
            "평단가":  st.column_config.NumberColumn("평단가 (₩)", min_value=0, format="%d"),
            "현재가":  st.column_config.NumberColumn("현재가 (자동)", disabled=True, format="%d"),
            "원금":    st.column_config.NumberColumn("원금 (자동)", disabled=True, format="%d"),
            "평가액":  st.column_config.NumberColumn("평가액 (자동)", disabled=True, format="%d"),
        },
        disabled=is_closed,
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
            else:
                st.warning(f"⚠️ \'{name}\' 현재가 조회 실패 (종목명 확인 필요)")
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
            prin  = _si(row.get("원금")) or int(avg_p * qty)
            val   = _si(row.get("평가액")) or int(cur_p * qty) or int(avg_p * qty)
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
    st.markdown("<div style=\'margin-top:8px;\'></div>", unsafe_allow_html=True)

    if sel_acc in STOCK_INPUT_ACCOUNTS:
        _render_stock_editor(owner, sel_acc)
    else:
        _render_principal_editor(owner, sel_acc)


with tab_jy_edit:
    render_edit_form("준영")

with tab_jd_edit:
    render_edit_form("지윤")
'''

content = content[:bot_start] + NEW_BOTTOM_BLOCK

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! File written.")
