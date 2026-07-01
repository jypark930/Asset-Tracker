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

cat_colors = ["#ff6b00", "#1b263b", "#3b82f6", "#94a3b8", "#f97316", "#475569"]

if txns:
    cat_sum = {c: 0 for c in CATEGORIES}
    for t in txns:
        cat_sum[t["category"]] = cat_sum.get(t["category"], 0) + t["amount"]
    total_v = sum(t["amount"] for t in txns)
    cat_items = sorted(cat_sum.items(), key=lambda x: -x[1])

    # ── 시각화 영역 (막대 차트 고정) ────────────────────────
    import plotly.graph_objects as go

    cats = [c for c, _ in cat_items]
    amts = [a for _, a in cat_items]
    bar_colors = [cat_colors[i % len(cat_colors)] for i in range(len(cats))]
    fig = go.Figure(go.Bar(
        x=cats, y=amts,
        marker_color=bar_colors,
        text=[f"₩{a:,}" for a in amts],
        textposition="outside",
        hoverinfo="none",
    ))
    fig.update_layout(
        height=320, margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        xaxis=dict(showgrid=False, tickfont=dict(size=13, color="#1e293b"), fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickformat=",.0f",
                   tickprefix="₩", tickfont=dict(size=11, color="#64748b"), fixedrange=True),
        font=dict(family="sans-serif"),
        dragmode=False,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "staticPlot": True,   # 모든 인터랙션 비활성화
            "displayModeBar": False,
        }
    )

    draw_neon_divider()

    # ── 카테고리별 요약 카드 (전월비 포함) ──────────────────────────────
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year  if month > 1 else year - 1
    prev_txns = get_transactions(prev_year, prev_month)
    prev_cat_sum = {}
    if prev_txns:
        for t in prev_txns:
            prev_cat_sum[t["category"]] = prev_cat_sum.get(t["category"], 0) + t["amount"]
    prev_total_v = sum(t["amount"] for t in prev_txns) if prev_txns else 0

    def get_mom_badge(curr, prev):
        if prev == 0 and curr == 0:
            return "<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#f8fafc;color:#94a3b8;font-size:0.75rem;font-weight:700;'>- 변동 없음</div>"
        
        delta = curr - prev
        
        if delta > 0:
            return f"<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#fee2e2;color:#ef4444;font-size:0.75rem;font-weight:700;'>+{delta:,}원</div>"
        elif delta < 0:
            return f"<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#dcfce7;color:#16a34a;font-size:0.75rem;font-weight:700;'>{delta:,}원</div>"
        else:
            return "<div style='margin-top:8px;display:inline-block;padding:3px 8px;border-radius:12px;background:#f8fafc;color:#94a3b8;font-size:0.75rem;font-weight:700;'>- 변동 없음</div>"

    cards_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;'>"
    for idx, (cat, amt) in enumerate(cat_items):
        color = cat_colors[idx % len(cat_colors)]
        badge = get_mom_badge(amt, prev_cat_sum.get(cat, 0))
        cards_html += f"""
        <div style='background:#fff;border:1px solid #e2e8f0;border-radius:12px;
                    padding:14px 16px;min-width:110px;flex:1;
                    box-shadow:0 4px 12px rgba(0,0,0,0.03);text-align:center;'>
          <div style='width:24px;height:3px;background:{color};border-radius:2px;margin:0 auto 8px;'></div>
          <div style='font-size:0.75rem;color:#64748b;font-weight:600;margin-bottom:6px;'>{cat}</div>
          <div style='font-size:1.1rem;font-weight:800;color:#1e293b;'>&#8361;{amt:,}</div>
          {badge}
        </div>"""
    
    # 합계 카드
    tot_badge = get_mom_badge(total_v, prev_total_v)
    cards_html += f"""
        <div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;
                    padding:14px 16px;min-width:130px;flex:1;
                    box-shadow:0 4px 12px rgba(0,0,0,0.03);text-align:center;'>
          <div style='width:24px;height:3px;background:#ff6b00;border-radius:2px;margin:0 auto 8px;'></div>
          <div style='font-size:0.75rem;color:#ff6b00;font-weight:600;margin-bottom:6px;'>변동지출 합계</div>
          <div style='font-size:1.15rem;font-weight:800;color:#ff6b00;'>&#8361;{total_v:,}</div>
          {tot_badge}
        </div>"""

    def merge_data(curr_raw, prev_raw):
        curr = curr_raw or {}
        prev = prev_raw or {}
        cf = curr.get("confirmed_fields")
        if cf is None or not isinstance(cf, list):
            if curr.get("updated_by") == "시스템":
                cf = [k for k, v in curr.items() if isinstance(v, (int, float)) and k not in ("id", "year", "month", "user_id")]
            else:
                cf = []
        res = {}
        all_keys = set(curr.keys()) | set(prev.keys())
        for k in all_keys:
            if k in ("id", "year", "month", "user_id", "updated_by", "updated_at", "created_at", "confirmed_fields"):
                continue
            if k in cf:
                res[k] = curr.get(k, 0)
            else:
                res[k] = prev.get(k, 0)
        return res

    prev_month = month - 1 if month > 1 else 12
    prev_year  = year  if month > 1 else year - 1

    inc_raw = get_monthly_income(year, month)
    fixed_raw = get_fixed_costs(year, month)
    util_raw = get_utility_costs(year, month)
    
    prev_inc_raw = get_monthly_income(prev_year, prev_month)
    prev_fixed_raw = get_fixed_costs(prev_year, prev_month)
    prev_util_raw = get_utility_costs(prev_year, prev_month)
    
    inc = merge_data(inc_raw, prev_inc_raw)
    fixed = merge_data(fixed_raw, prev_fixed_raw)
    util = merge_data(util_raw, prev_util_raw)
    
    def g(d, k): return int(d.get(k, 0) or 0)
    
    jy_tot = g(inc,"junyoung_salary") + g(inc,"junyoung_bonus")
    jd_tot = g(inc,"jiyun_salary") + g(inc,"jiyun_incentive")
    from utils.db import get_other_incomes
    other_inc = sum(item.get("amount", 0) for item in get_other_incomes(year, month))
    total_income = jy_tot + jd_tot + other_inc
    
    housing   = g(fixed,"loan_payment") + g(fixed,"rent") + g(fixed,"maintenance_fee")
    car_ins   = g(fixed,"car_insurance") + g(fixed,"driver_insurance") + g(fixed,"health_insurance") + g(fixed,"cancer_insurance")
    telecom   = g(fixed,"junyoung_phone") + g(fixed,"jiyun_phone") + g(fixed,"internet")
    transport = g(fixed,"junyoung_transport") + g(fixed,"jiyun_transport") + g(fixed,"fuel") + g(fixed,"hipass")
    misc      = g(fixed,"junyoung_club") + g(fixed,"jiyun_club") + g(fixed,"junyoung_parents") + g(fixed,"jiyun_parents")
    subs      = g(fixed,"coupang") + g(fixed,"youtube") + g(fixed,"naver")
    savings   = g(fixed,"junyoung_savings1") + g(fixed,"junyoung_savings2") + g(fixed,"jiyun_savings1") + g(fixed,"jiyun_savings2")
    allowance = g(fixed,"junyoung_allowance") + g(fixed,"jiyun_allowance")
    total_fixed = housing + g(fixed,"car_tax") + car_ins + telecom + transport + misc + subs + savings + allowance
    
    livable = total_income - total_fixed
    
    total_utility = g(util,"electricity") + g(util,"water") + g(util,"gas")
    
    cat_sum_3 = {}
    for t in txns:
        c = t.get("category","기타")
        cat_sum_3[c] = cat_sum_3.get(c,0) + t.get("amount",0)
        
    daily_total = int(cat_sum_3.get("생활비",0)) + int(cat_sum_3.get("간식비",0)) + int(cat_sum_3.get("외식비",0)) + int(cat_sum_3.get("문화비",0)) + int(cat_sum_3.get("준영점심",0))
    medical = int(cat_sum_3.get("의료비", 0))
    gift = int(cat_sum_3.get("경조비",0))
    total_variable = total_utility + daily_total + medical + gift
    
    investable = livable - total_variable
    
    cards_html += f"""
        <div style='background:#f0fdf4;border:1px solid #86efac;border-radius:12px;
                    padding:14px 16px;min-width:130px;flex:1;
                    box-shadow:0 4px 12px rgba(0,0,0,0.03);text-align:center;'>
          <div style='width:24px;height:3px;background:#10b981;border-radius:2px;margin:0 auto 8px;'></div>
          <div style='font-size:0.75rem;color:#10b981;font-weight:600;margin-bottom:6px;'>익월 투자 가능</div>
          <div style='font-size:1.15rem;font-weight:800;color:#10b981;'>&#8361;{investable:,}</div>
        </div>"""
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
    draw_neon_divider()

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
