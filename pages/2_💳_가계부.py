"""
pages/2_💳_가계부.py  ─  수입 / 변동지출 / 고정비 / 공과금 관리
"""
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="가계부 | Asset Tracker", page_icon="💳", layout="wide")

from utils.auth import is_authenticated, try_restore_session
from utils.db import (
    CATEGORIES, FIXED_COST_LABELS, FIXED_COST_GROUPS,
    get_transactions, insert_transaction, update_transaction, delete_transaction,
    get_monthly_income, upsert_monthly_income,
    get_fixed_costs, upsert_fixed_costs,
    get_utility_costs, upsert_utility_costs,
)

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("app.py")

now = datetime.now()
st.title("💳 가계부")

# ── 월 선택 ──────────────────────────────────────────────
cy, cm, _ = st.columns([1, 1, 5])
with cy:
    year  = st.selectbox("연도", [2025, 2026, 2027], index=1, key="bk_year")
with cm:
    month = st.selectbox("월", list(range(1, 13)), index=now.month - 1, key="bk_month")

st.divider()

# ── 탭 ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🛒 변동지출", "💰 수입", "🔒 고정비", "⚡ 공과금"])


# ═══════════════════════════════════════════════════════════
# TAB 1 : 변동지출
# ═══════════════════════════════════════════════════════════
with tab1:
    st.subheader("🛒 변동지출 관리")

    txns = get_transactions(year, month)

    # ── 카테고리별 합계 (최상단) ─────────────────────────────
    if txns:
        cat_sum = {}
        for t in txns:
            cat_sum[t["category"]] = cat_sum.get(t["category"], 0) + t["amount"]
        total_v = sum(t["amount"] for t in txns)

        st.subheader("📊 카테고리별 합계")
        # 카테고리별 메트릭 카드로 표시
        cat_items = sorted(cat_sum.items(), key=lambda x: -x[1])
        cols = st.columns(min(len(cat_items), 4))
        for i, (cat, amt) in enumerate(cat_items):
            cols[i % 4].metric(cat, f"₩{amt:,}")
        st.metric("**💰 변동지출 총합계**", f"₩{total_v:,}")

        st.divider()

    # ── 달력 뷰 (일별 합계) ──────────────────────────────────
    st.subheader("📅 월별 달력")

    import calendar
    day_sum = {}
    day_details = {}
    for t in txns:
        d = t["day"]
        day_sum[d] = day_sum.get(d, 0) + t["amount"]
        if d not in day_details:
            day_details[d] = []
        day_details[d].append(t)

    # 일요일(6) 시작으로 설정
    cal = calendar.monthcalendar(year, month)
    # Python 기본은 월요일 시작이므로 일요일 시작으로 재계산
    c = calendar.Calendar(firstweekday=6)
    cal = c.monthdayscalendar(year, month)
    weekdays = ["일", "월", "화", "수", "목", "금", "토"]

    # 달력 HTML 생성
    cal_html = """
<style>
.cal-table { width:100%; border-collapse:collapse; font-family:sans-serif; }
.cal-table th { 
    background:#1e1b4b; color:#a5b4fc; text-align:center; 
    padding:8px; font-size:14px; border:1px solid #333;
}
.cal-table th.sat { color:#60a5fa; }
.cal-table th.sun { color:#f87171; }
.cal-table td { 
    border:1px solid #333; padding:8px; vertical-align:top; 
    min-height:70px; background:#0f0e1a; 
}
.cal-table td.empty { background:#0a0918; }
.cal-table td.today { background:#1e1b4b; border:2px solid #a78bfa; }
.day-num { font-size:13px; color:#9ca3af; margin-bottom:4px; }
.day-num.sat { color:#60a5fa; }
.day-num.sun { color:#f87171; }
.day-amt { font-size:14px; font-weight:bold; color:#34d399; }
</style>
<table class="cal-table">
<tr>
"""
    for i, wd in enumerate(weekdays):
        # 일(0)=빨강, 토(6)=파랑
        cls = "sun" if i == 0 else ("sat" if i == 6 else "")
        cal_html += f'<th class="{cls}">{wd}</th>'
    cal_html += "</tr>"

    today = datetime.now()

    for week in cal:
        cal_html += "<tr>"
        for col_i, day in enumerate(week):
            if day == 0:
                cal_html += '<td class="empty"></td>'
            else:
                is_today = (today.year == year and today.month == month and today.day == day)
                td_class = "today" if is_today else ""
                # col_i==0 → 일요일, col_i==6 → 토요일
                day_cls = "sun" if col_i == 0 else ("sat" if col_i == 6 else "")
                amt = day_sum.get(day, 0)
                amt_str = f'<div class="day-amt">₩{amt:,}</div>' if amt > 0 else ""
                cal_html += f'<td class="{td_class}"><div class="day-num {day_cls}">{day}</div>{amt_str}</td>'
        cal_html += "</tr>"

    cal_html += "</table>"
    st.markdown(cal_html, unsafe_allow_html=True)

    st.divider()

    # ── 추가 폼 ──────────────────────────────────────────
    with st.expander("➕ 새 지출 추가", expanded=False):
        with st.form("add_tx_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                f_day   = st.number_input("일", 1, 31, today.day)
                f_amt   = st.number_input("금액 (₩)", 0, step=1000, format="%d")
                if f_amt > 0:
                    st.caption(f"₩{int(f_amt):,}")
            with fc2:
                f_cat   = st.selectbox("구분", CATEGORIES)
                f_desc  = st.text_input("이용처")
            if st.form_submit_button("💾 저장", use_container_width=True):
                if f_amt <= 0:
                    st.error("금액을 입력하세요.")
                elif insert_transaction(year, month, f_day, f_amt, f_desc, f_cat):
                    from utils.audio import play_notice_sound
                    play_notice_sound()
                    st.success("✅ 저장되었습니다.")
                    st.rerun()

    st.write("")

    # ── 내역 테이블 (편집 가능) ───────────────────────────
    if not txns:
        st.info(f"📌 {year}년 {month}월 변동지출 내역이 없습니다.")
    else:
        df = pd.DataFrame(txns)
        df_edit = df[["id", "day", "amount", "description", "category"]].copy()
        df_edit.insert(0, "삭제", False)

        edited = st.data_editor(
            df_edit,
            column_config={
                "삭제":        st.column_config.CheckboxColumn("🗑️ 삭제", width="small"),
                "id":          None,
                "day":         st.column_config.NumberColumn("일", min_value=1, max_value=31, width="small"),
                "amount":      st.column_config.NumberColumn("금액(₩)", min_value=0, format="%d"),
                "description": st.column_config.TextColumn("이용처"),
                "category":    st.column_config.SelectboxColumn("구분", options=CATEGORIES),
            },
            hide_index=True,
            use_container_width=True,
            key=f"tx_editor_{year}_{month}",
        )

        b1, b2, _ = st.columns([1, 1, 5])
        with b1:
            if st.button("💾 수정 저장", use_container_width=True):
                changed = 0
                for idx, row in edited.iterrows():
                    if row["삭제"]:
                        continue
                    orig = df[df["id"] == row["id"]].iloc[0]
                    diff = {}
                    if int(row["day"])    != int(orig["day"]):         diff["day"]         = int(row["day"])
                    if int(row["amount"]) != int(orig["amount"]):      diff["amount"]      = int(row["amount"])
                    if row["description"] != orig["description"]:      diff["description"] = row["description"]
                    if row["category"]    != orig["category"]:         diff["category"]    = row["category"]
                    if diff:
                        update_transaction(row["id"], diff)
                        changed += 1
                if changed:
                    from utils.audio import play_notice_sound
                    play_notice_sound()
                    st.success(f"✅ {changed}건 수정 완료")
                    st.rerun()
                else:
                    st.info("변경된 내용이 없습니다.")

        with b2:
            to_del = edited[edited["삭제"] == True]["id"].tolist()
            if st.button(f"🗑️ 선택 삭제 ({len(to_del)}건)", use_container_width=True,
                         disabled=len(to_del) == 0):
                for tid in to_del:
                    delete_transaction(tid)
                from utils.audio import play_notice_sound
                play_notice_sound()
                st.success(f"✅ {len(to_del)}건 삭제 완료")
                st.rerun()



# ═══════════════════════════════════════════════════════════
# TAB 2 : 수입
# ═══════════════════════════════════════════════════════════
with tab2:
    st.subheader("💰 월별 수입 입력")
    income = get_monthly_income(year, month)
    if not income or not income.get("updated_by"):
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        income = get_monthly_income(prev_y, prev_m)
        if income: st.info(f"💡 이번 달 수입이 아직 확정되지 않아 **전월({prev_m}월)** 데이터가 기본값으로 불러와졌습니다.")

    with st.form("income_form"):
        st.markdown("**👨 준영**")
        ic1, ic2 = st.columns(2)
        jy_sal = ic1.number_input("정기급여 (₩)", 0, value=income.get("junyoung_salary", 0), step=10000, key="jy_sal", format="%d")
        ic1.caption(f"₩{int(jy_sal):,}")
        jy_bon = ic2.number_input("상여금 (₩)",   0, value=income.get("junyoung_bonus", 0),  step=10000, key="jy_bon", format="%d")
        ic2.caption(f"₩{int(jy_bon):,}")

        st.markdown("**👩 지윤**")
        id1, id2 = st.columns(2)
        jd_sal = id1.number_input("정기급여 (₩)", 0, value=income.get("jiyun_salary", 0),    step=10000, key="jd_sal", format="%d")
        id1.caption(f"₩{int(jd_sal):,}")
        jd_inc = id2.number_input("인센티브 (₩)", 0, value=income.get("jiyun_incentive", 0), step=10000, key="jd_inc", format="%d")
        id2.caption(f"₩{int(jd_inc):,}")

        total_in = jy_sal + jy_bon + jd_sal + jd_inc
        st.metric("총 가구 수입", f"₩{total_in:,}")

        if st.form_submit_button("💾 저장", use_container_width=True):
            payload = {
                "junyoung_salary":   jy_sal,
                "junyoung_bonus":    jy_bon,
                "jiyun_salary":      jd_sal,
                "jiyun_incentive":   jd_inc,
            }
            if upsert_monthly_income(year, month, payload, confirmed_fields=list(payload.keys())):
                from utils.audio import play_notice_sound
                play_notice_sound()
                st.success("✅ 수입 정보가 저장되었습니다.")
                st.rerun()


# ═══════════════════════════════════════════════════════════
# TAB 3 : 고정비
# ═══════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔒 고정비 입력")
    fixed = get_fixed_costs(year, month)
    if not fixed or not fixed.get("updated_by"):
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        fixed = get_fixed_costs(prev_y, prev_m)
        if fixed: st.info(f"💡 이번 달 고정비가 아직 확정되지 않아 **전월({prev_m}월)** 데이터가 기본값으로 불러와졌습니다.")

    with st.form("fixed_form"):
        new_fixed = {}
        for group_name, fields in FIXED_COST_GROUPS.items():
            st.markdown(f"**{group_name}**")
            cols = st.columns(min(len(fields), 3))
            for i, field in enumerate(fields):
                label = FIXED_COST_LABELS[field]
                val   = fixed.get(field, 0)
                v = cols[i % 3].number_input(
                    label, 0, value=val, step=1000, key=f"fix_{field}", format="%d"
                )
                cols[i % 3].caption(f"₩{int(v):,}")
                new_fixed[field] = v

        total_f = sum(new_fixed.values())
        st.metric("고정비 합계", f"₩{total_f:,}")

        if st.form_submit_button("💾 저장", use_container_width=True):
            if upsert_fixed_costs(year, month, new_fixed, confirmed_fields=list(new_fixed.keys())):
                from utils.audio import play_notice_sound
                play_notice_sound()
                st.success("✅ 고정비가 저장되었습니다.")
                st.rerun()


# ═══════════════════════════════════════════════════════════
# TAB 4 : 공과금
# ═══════════════════════════════════════════════════════════
with tab4:
    st.subheader("⚡ 공과금 입력")
    util = get_utility_costs(year, month)
    if not util or not util.get("updated_by"):
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        util = get_utility_costs(prev_y, prev_m)
        if util: st.info(f"💡 이번 달 공과금이 아직 확정되지 않아 **전월({prev_m}월)** 데이터가 기본값으로 불러와졌습니다.")

    with st.form("util_form"):
        uc1, uc2, uc3 = st.columns(3)
        elec  = uc1.number_input("⚡ 전기세 (₩)", 0, value=util.get("electricity", 0), step=1000, format="%d")
        uc1.caption(f"₩{int(elec):,}")
        water = uc2.number_input("💧 수도세 (₩)", 0, value=util.get("water", 0),       step=1000, format="%d")
        uc2.caption(f"₩{int(water):,}")
        gas   = uc3.number_input("🔥 가스비 (₩)", 0, value=util.get("gas", 0),         step=1000, format="%d")
        uc3.caption(f"₩{int(gas):,}")

        total_u = elec + water + gas
        st.metric("공과금 합계", f"₩{total_u:,}")

        if st.form_submit_button("💾 저장", use_container_width=True):
            payload = {
                "electricity": elec, "water": water, "gas": gas,
            }
            if upsert_utility_costs(year, month, payload, confirmed_fields=list(payload.keys())):
                from utils.audio import play_notice_sound
                play_notice_sound()
                st.success("✅ 공과금이 저장되었습니다.")
                st.rerun()
