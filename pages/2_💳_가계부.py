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
        st.switch_page("0_🏠_홈.py")

now = datetime.now()

def draw_neon_divider():
    st.markdown("""
    <hr style="height:1px;border:none;background:#e2e8f0;margin:16px 0;">
    """, unsafe_allow_html=True)

# ── 커스텀 네온 타이틀 ─────────────────────────
st.markdown("""
<div style="width: 100%; display: flex; justify-content: center; margin-bottom: 4px; margin-top: 10px;">
    <h1 style="font-size: 1.8rem; font-weight: 800; color: #1e293b; margin: 0 auto; text-align: center !important; width: 100%;">
        가계부
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

# ── 탭 ───────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════

txns = get_transactions(year, month)
selected_category = None


# ── 달력 뷰 (일별 합계) ──────────────────────────────────
st.subheader("📅 월별 달력")

import calendar, json
import streamlit.components.v1 as components

day_sum = {}
day_details = {}
for t in txns:
    d = t["day"]
    day_sum[d] = day_sum.get(d, 0) + t["amount"]
    if d not in day_details:
        day_details[d] = []
    day_details[d].append(t)

# 일요일 시작으로 달력 계산
c_obj = calendar.Calendar(firstweekday=6)
cal = c_obj.monthdayscalendar(year, month)
weekdays = ["일", "월", "화", "수", "목", "금", "토"]

today = datetime.now()

# ── 팝업 상세 데이터 JSON 구성 ──────────────────────────
day_detail_json = {}
for d, items in day_details.items():
    entries = []
    for t in items:
        entries.append({
            "desc": t.get("description", "-") or "-",
            "cat": t.get("category", "-") or "-",
            "amt": t["amount"]
        })
    day_detail_json[str(d)] = entries

detail_json_str = json.dumps(day_detail_json, ensure_ascii=False)
n_weeks = len(cal)
cal_height = n_weeks * 77 + 50  # 헤더(36px) + 여백(14px)

# ── 달력 HTML 빌드 (components.v1.html 로 렌더링하여 JS 팝업 동작) ──
cal_body = ""
for i, wd in enumerate(weekdays):
    cls = "sun" if i == 0 else ("sat" if i == 6 else "")
    cal_body += f'<th class="{cls}">{wd}</th>'
cal_body = f"<tr>{cal_body}</tr>"

for week in cal:
    row = ""
    for col_i, day in enumerate(week):
        if day == 0:
            row += '<td class="empty"></td>'
        else:
            is_today = (today.year == year and today.month == month and today.day == day)
            td_class = "today" if is_today else ""
            day_cls = "sun" if col_i == 0 else ("sat" if col_i == 6 else "")
            amt = day_sum.get(day, 0)
            amt_str = f'<span class="day-amt">&#8361;{amt:,}</span>' if amt > 0 else ""
            onclick = f' onclick="showDayPopup({day}, event)"' if amt > 0 else ""
            row += f'<td class="{td_class}"{onclick}><span class="day-num {day_cls}">{day}</span>{amt_str}</td>'
    cal_body += f"<tr>{row}</tr>"

full_html = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
    "*{box-sizing:border-box;margin:0;padding:0}"
    "body{background:transparent;font-family:'Segoe UI',sans-serif;overflow-x:hidden}"
    ".cal-table{width:100%;table-layout:fixed;border-collapse:collapse}"
    ".cal-table th{background:#f8fafc;color:#475569;text-align:center;padding:8px 4px;font-size:13px;border:1px solid #e2e8f0;font-weight:700}"
    ".cal-table th.sat{color:#3b82f6}.cal-table th.sun{color:#ef4444}"
    ".cal-table td{border:1px solid #e2e8f0;vertical-align:top;background:#fff;height:76px;cursor:pointer;transition:background .12s;overflow:hidden;padding:6px 5px 4px 5px;user-select:none}"
    ".cal-table td:hover{background:#f0f9ff}"
    ".cal-table td.empty{background:#f8fafc;cursor:default}.cal-table td.empty:hover{background:#f8fafc}"
    ".cal-table td.today{background:#fff7ed;border:2px solid #ff6b00}"
    ".day-num{font-size:12px;color:#94a3b8;font-weight:600;display:block;margin-bottom:3px}"
    ".day-num.sat{color:#3b82f6}.day-num.sun{color:#ef4444}"
    ".day-amt{font-size:11px;font-weight:700;color:#ff6b00;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    "#cal-popup{display:none;position:fixed;z-index:9999;background:#fff;border:1px solid #e2e8f0;"
    "border-radius:14px;box-shadow:0 8px 36px rgba(0,0,0,.22);padding:16px 20px 12px;"
    "min-width:230px;max-width:300px;max-height:380px;overflow-y:auto;cursor:pointer;font-family:'Segoe UI',sans-serif}"
    ".popup-title{font-size:.95rem;font-weight:800;color:#1e293b;margin-bottom:10px;border-bottom:2px solid #ff6b00;padding-bottom:6px}"
    ".popup-item{display:flex;align-items:center;padding:5px 0;border-bottom:1px solid #f1f5f9;gap:7px}"
    ".popup-item:last-of-type{border-bottom:none}"
    ".popup-cat{font-size:.68rem;color:#fff;background:#ff6b00;border-radius:4px;padding:1px 5px;white-space:nowrap;flex-shrink:0}"
    ".popup-desc{font-size:.8rem;color:#1e293b;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    ".popup-amt{font-size:.82rem;font-weight:700;color:#ff6b00;white-space:nowrap;flex-shrink:0}"
    ".popup-total{margin-top:8px;text-align:right;font-size:.85rem;font-weight:800;color:#1b263b;border-top:1px solid #e2e8f0;padding-top:7px}"
    ".popup-hint{text-align:center;font-size:.68rem;color:#94a3b8;margin-top:5px}"
    "</style></head><body>"
    "<div id='cal-popup'></div>"
    "<table class='cal-table'>" + cal_body + "</table>"
    "<script>"
    "var DAY_DETAILS=" + detail_json_str + ";"
    "function showDayPopup(day,event){"
    "  event.stopPropagation();"
    "  var d=DAY_DETAILS[String(day)],p=document.getElementById('cal-popup');"
    "  if(!d||d.length===0){p.style.display='none';return;}"
    "  var html='<div class=\"popup-title\">&#128197; '+day+'일 지출 내역</div>',total=0;"
    "  d.forEach(function(item){"
    "    total+=item.amt;"
    "    html+='<div class=\"popup-item\"><span class=\"popup-cat\">'+item.cat+'</span>'"
    "         +'<span class=\"popup-desc\">'+item.desc+'</span>'"
    "         +'<span class=\"popup-amt\">&#8361;'+item.amt.toLocaleString('ko-KR')+'</span></div>';"
    "  });"
    "  html+='<div class=\"popup-total\">합계: &#8361;'+total.toLocaleString('ko-KR')+'</div>';"
    "  html+='<div class=\"popup-hint\">&#9660; 클릭하면 닫힙니다</div>';"
    "  p.innerHTML=html;"
    "  var r=event.currentTarget.getBoundingClientRect(),pw=300,ph=380;"
    "  var px=r.left,py=r.bottom+6;"
    "  if(px+pw>window.innerWidth-10)px=window.innerWidth-pw-10;"
    "  if(py+ph>window.innerHeight-10)py=r.top-ph-6;"
    "  if(py<4)py=4;if(px<4)px=4;"
    "  p.style.left=px+'px';p.style.top=py+'px';p.style.display='block';"
    "}"
    "document.getElementById('cal-popup').addEventListener('click',function(e){e.stopPropagation();this.style.display='none';});"
    "document.addEventListener('click',function(){var p=document.getElementById('cal-popup');if(p)p.style.display='none';});"
    "</script></body></html>"
)

components.html(full_html, height=cal_height, scrolling=False)



# ── 추가 폼 ──────────────────────────────────────────
with st.expander("➕ 새 지출 추가", expanded=False):
    st.markdown("""
    <style>
    /* 새 지출 추가 폼 내 '일' 입력칸 텍스트 중앙정렬 */
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stNumberInput"] input {
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    with st.form("add_tx_form", clear_on_submit=True):
        fc1, fc2 = st.columns([1, 6])  # 일 컬럼을 좁게 설정
        with fc1:
            # 해당 월의 마지막으로 입력한 '일'을 기억 (없으면 이번 달인 경우 오늘, 아니면 1일)
            default_day = st.session_state.get(f"last_day_{year}_{month}", today.day if (year == today.year and month == today.month) else 1)
            # 해당 월의 최대 일수를 계산 (윤년 포함)
            import calendar
            max_day = calendar.monthrange(year, month)[1]
            if default_day > max_day:
                default_day = max_day
                
            f_day = st.number_input("일", 1, max_day, default_day)
        with fc2:
            f_cat = st.selectbox("구분", CATEGORIES)

        fc3, fc4 = st.columns(2)
        with fc3:
            f_amt_str = st.text_input("금액 (₩)", placeholder="예: 10,000")
        with fc4:
            f_desc = st.text_input("이용처")
        if st.form_submit_button("💾 저장", use_container_width=True):
            # 금액 문자열에서 콤마 제거 및 정수 변환
            try:
                f_amt = int(f_amt_str.replace(",", "").strip())
            except ValueError:
                f_amt = 0

            if f_amt <= 0:
                st.error("올바른 금액을 입력하세요.")
            elif insert_transaction(year, month, f_day, f_amt, f_desc, f_cat):
                # 방금 입력한 '일'을 세션 상태에 저장하여 다음 입력 시 기본값으로 사용
                st.session_state[f"last_day_{year}_{month}"] = f_day
                
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
            "삭제":        st.column_config.CheckboxColumn("", width=50),
            "id":          None,
            "day":         st.column_config.NumberColumn("일", min_value=1, max_value=31, width=45, alignment="center"),
            "amount":      st.column_config.NumberColumn("금액(₩)", min_value=0, format="₩%,d"),
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

draw_neon_divider()


# ── 카테고리 필터 (pills) ──────────────────────
if txns:
    _cats_avail = sorted({t["category"] for t in txns if t.get("category")})
    _sel = st.pills("🔍 카테고리 필터", options=["🌟 전체보기"] + _cats_avail, default="🌟 전체보기")
    if _sel and _sel != "🌟 전체보기":
        selected_category = _sel

# ── 변동지출 내역 ──────────────────────
if selected_category:
    st.markdown(f"<p style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:8px;'>🧾 {year}년 {month}월 <span style='color:#ff6b00;'>[{selected_category}]</span> 지출 내역</p>", unsafe_allow_html=True)
else:
    st.markdown(f"<p style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:8px;'>🧾 {year}년 {month}월 전체 변동지출 내역</p>", unsafe_allow_html=True)

if txns:
    df_list = pd.DataFrame(txns)[["day", "category", "description", "amount"]]
    df_list.columns = ["일", "구분", "이용처", "금액(원)"]
    
    # 선택된 카테고리가 있으면 필터링
    if selected_category:
        df_list = df_list[df_list["구분"] == selected_category]
        
    if len(df_list) > 0:
        sum_amt = df_list["금액(원)"].sum()
        df_list["금액(원)"] = df_list["금액(원)"].apply(lambda x: f"₩{x:,}")
        
        # 커스텀 HTML 테이블 (중앙 정렬 및 완벽한 너비 조절)
        html = "<div style='overflow-x: auto;'>"
        html += "<table style='width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95rem; text-align: center; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.03); font-family: \"KoPubWorldDotum\", sans-serif;'>"
        html += "<tr style='background-color: #f8f9fa; border-bottom: 2px solid #e2e8f0; color: #64748b; font-weight: 700;'>"
        html += "<th style='padding: 12px 8px; width: 16%; text-align: center;'>일</th>"
        html += "<th style='padding: 12px 8px; width: 22%; text-align: center;'>구분</th>"
        html += "<th style='padding: 12px 8px; text-align: center;'>이용처</th>"
        html += "<th style='padding: 12px 12px; width: 1%; white-space: nowrap; text-align: center;'>금액(원)</th>"
        html += "</tr>"
        
        for idx, row in df_list.iterrows():
            html += "<tr style='border-bottom: 1px solid #f1f5f9; background-color: #ffffff;'>"
            html += f"<td style='padding: 12px 8px; width: 16%; color: #1e293b; font-weight: 700;'>{row['일']}</td>"
            html += f"<td style='padding: 12px 8px; width: 22%; color: #475569;'>{row['구분']}</td>"
            html += f"<td style='padding: 12px 8px; color: #1e293b;'>{row['이용처']}</td>"
            html += f"<td style='padding: 12px 12px; width: 1%; white-space: nowrap; color: #1e293b; text-align: right; font-weight: 600;'>{row['금액(원)']}</td>"
            html += "</tr>"
            
        html += "</table></div>"
        st.markdown(html, unsafe_allow_html=True)
        
        st.caption(f"총 {len(df_list)}건 / 합계 ₩{sum_amt:,}")
    else:
        st.info(f"📌 '{selected_category}' 카테고리의 지출 내역이 없습니다.")
else:
    st.info("📌 변동지출 내역이 없습니다. 가계부 메뉴에서 입력하세요.")
