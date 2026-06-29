"""
pages/5_📋_재무현황.py  ─  수입/지출 구조 종합 현황
항목/금액/수정자/수정일 테이블 | 섹션별 인라인 수정 | 전월 자동 불러오기
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="재무현황 | Asset Tracker", page_icon="📋", layout="wide")

from utils.auth import (
    is_authenticated, try_restore_session,
    EMAIL_TO_NAME, get_current_user_email,
)
from utils.db import (
    get_monthly_income, upsert_monthly_income,
    get_fixed_costs,   upsert_fixed_costs,
    get_utility_costs, upsert_utility_costs,
    get_transactions,  get_investments,
    get_other_incomes, insert_transaction, delete_transaction
)

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("0_🏠_홈.py")

now = datetime.now()

def draw_neon_divider():
    st.markdown('<hr style="height:1px;border:none;background:#e2e8f0;margin:16px 0;">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# ■ CSS (라이트 테마)
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
/* 1. 스트림릿 마크다운 텍스트의 불필요한 위아래 여백 제거 */
div[data-testid="stMarkdownContainer"] > p {
    margin-bottom: 0 !important;
}

/* 2. 항목 타이틀의 네모난 박스와 그림자 디자인을 제거하고, 
      깔끔하게 폰트 크기와 색상으로만 구분 (표의 각 셀이 하나로 이어져 보이게 함) */
.fin-h1 {
    color: #1e293b;
    font-weight: 800;
    font-size: 1.1rem;
    padding: 8px 0 8px 10px;
    border-left: 4px solid #ff6b00;
    display: flex;
    align-items: center;
    min-height: 40px;
}
.fin-h2 {
    color: #1e293b;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 6px 0 6px 14px;
    border-left: 3px solid #1b263b;
    display: flex;
    align-items: center;
    min-height: 40px;
}
.fin-h3 {
    font-size: 0.85rem;
    font-weight: 600;
    color: #475569;
    padding: 4px 0 4px 24px;
    display: flex;
    align-items: center;
    min-height: 40px;
}
.fin-calc {
    color: #059669;
    font-weight: 800;
    font-size: 1.05rem;
    padding: 8px 0 8px 10px;
    border-left: 4px solid #10b981;
    display: flex;
    align-items: center;
    min-height: 40px;
}
.fin-inv {
    color: #2563eb;
    font-weight: 800;
    font-size: 1.05rem;
    padding: 8px 0 8px 10px;
    border-left: 4px solid #3b82f6;
    display: flex;
    align-items: center;
    min-height: 40px;
}
.tbl-hdr {
    font-size: 0.8rem;
    font-weight: 700;
    color: #64748b;
    text-align: center;
    padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}
.amt-container { 
    text-align: right; 
    display: flex; 
    align-items: center;
    justify-content: flex-end;
    width: 100%; 
    min-height: 40px;
    padding-right: 10px; 
}
.meta-container {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 40px;
}
.amt-pos  { color:#1e293b; font-weight:700; font-family:'KoPubWorldDotum',sans-serif; }
.amt-neg  { color:#ef4444; font-weight:700; font-family:'KoPubWorldDotum',sans-serif; }
.amt-grn  { color:#10b981; font-weight:800; font-family:'KoPubWorldDotum',sans-serif; }
.amt-yel  { color:#f59e0b; font-weight:800; font-family:'KoPubWorldDotum',sans-serif; }
.amt-dim  { color:#94a3b8; font-weight:500; }
.amt-unc  { color:#d97706; font-weight:600; font-family:'KoPubWorldDotum',sans-serif; }
.meta     { color:#64748b; font-size:0.8rem; font-weight:500; text-align:center; display:block; }
.tag-unc  { background:#fef3c7; color:#d97706; font-size:0.7rem; padding:2px 6px; border-radius:12px; font-weight:700; margin-left:6px; }

/* === 카드형 항목 (클릭 시 아코디언 토글) === */
.fin-row-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s;
}
.fin-row-container:hover {
    background-color: #f1f5f9;
}
.fin-row-label {
    font-weight: 700;
    color: #334155;
    font-size: clamp(0.85rem, 3vw, 1rem);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1 1 0;
    min-width: 0;
}
.fin-row-amount {
    font-weight: 600;
    font-size: clamp(0.85rem, 3vw, 1rem);
    white-space: nowrap;
    flex-shrink: 0;
}

/* 스트림릿 컨테이너 간격 제거 */
.element-container:has(.fin-row-container) {
    margin-bottom: 0 !important;
}

/* 아코디언(st.expander) 투명 오버레이 트릭 */
/* 전체 expander 껍데기 스타일 초기화 */
[data-testid="stExpander"] {
    position: relative !important;
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    margin-top: 0 !important;
}

/* expander 헤더(summary)를 위쪽 카드 위로 덮어씌움 (투명 클릭 영역) */
[data-testid="stExpander"] summary {
    position: absolute !important;
    top: -56px !important; /* 위 카드의 높이만큼 끌어올림 */
    left: 0 !important;
    width: 100% !important;
    height: 56px !important; /* 클릭 가능한 영역의 높이 */
    opacity: 0 !important; /* 완벽하게 투명화 */
    z-index: 10 !important; /* 위 카드 위에 띄움 */
    cursor: pointer !important;
}

/* 아코디언 내부 폼 영역 스타일 */
[data-testid="stExpander"] details {
    border: none !important;
}

[data-testid="stExpander"] .stExpanderContent {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 0 0 8px 8px !important;
    padding: 16px !important;
    margin-top: 0 !important;
    border-top: 1px dashed #e2e8f0 !important;
}

/* 폼 요소 간격 축소 */
[data-testid="stExpander"] .stNumberInput { margin-bottom: 8px !important; }
[data-testid="stExpander"] .stButton > button {
    width: 100%;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 6px;
}
</style>

""", unsafe_allow_html=True)

def _get_card_html(title: str, value: str, delta: str = "", border_color: str = "#ff6b00", delta_color: str = "#10b981"):
    delta_html = f"<div style='font-size: clamp(0.8rem, 3vw, 1rem);font-weight:600;color:{delta_color};margin-top:6px;white-space:nowrap;'>{delta}</div>" if delta else "<div style='font-size: clamp(0.8rem, 3vw, 1rem);font-weight:600;margin-top:6px;white-space:nowrap;visibility:hidden;'>&nbsp;</div>"
    return f"""<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: clamp(14px, 3vw, 24px) clamp(8px, 2vw, 16px); box-shadow: 0 4px 12px rgba(0,0,0,0.03); height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; overflow: hidden;">
<div style="width: 32px; height: 4px; background-color: {border_color}; border-radius: 2px; margin-bottom: clamp(8px, 2.5vw, 14px);"></div>
<div style="font-size: clamp(0.85rem, 3vw, 1.1rem);color:#64748b;font-weight:600;letter-spacing:0.02em;margin-bottom:8px;white-space:nowrap;">{title}</div>
<div style="font-size: clamp(1.2rem, 4.5vw, 1.8rem);font-weight:800;color:#1e293b;font-family:'KoPubWorldBold',monospace;line-height:1.2;letter-spacing:-0.5px;white-space:nowrap;">{value}</div>
{delta_html}
</div>"""

# ── 커스텀 타이틀 ─────────────────────────
st.markdown("""
<div style="width:100%;display:flex;justify-content:center;margin-bottom:4px;margin-top:10px;">
    <h1 style="font-size:1.8rem;font-weight:800;color:#1e293b;margin:0 auto;text-align:center !important;width:100%;">
        재무 현황
    </h1>
</div>
""", unsafe_allow_html=True)
st.caption("항목별 수정 가능 | 미입력 항목은 전월 데이터 자동 적용 후 (미확정) 표시")


# ── 월 선택 (◄ ► 네비게이션) ────────────────────────
if "fin_year" not in st.session_state:
    st.session_state.fin_year = now.year
if "fin_month" not in st.session_state:
    st.session_state.fin_month = now.month

def fin_prev_month():
    if st.session_state.fin_month == 1:
        st.session_state.fin_month = 12
        st.session_state.fin_year -= 1
    else:
        st.session_state.fin_month -= 1

def fin_next_month():
    if st.session_state.fin_month == 12:
        st.session_state.fin_month = 1
        st.session_state.fin_year += 1
    else:
        st.session_state.fin_month += 1

year  = st.session_state.fin_year
month = st.session_state.fin_month

nav_container = st.container()
with nav_container:
    st.button("◀", on_click=fin_prev_month, key="fin_prev_btn")
    st.markdown(f"""
    <div id="month-nav-marker" style='display: flex; align-items: center; justify-content: center; height: 42px; width: 140px; font-size: 1.2rem; font-weight: 700; color: #1e293b; margin: 0 auto;'>
        <span style="transform: translateY(-4px);">{year}년 {month}월</span>
    </div>
    """, unsafe_allow_html=True)
    st.button("▶", on_click=fin_next_month, key="fin_next_btn")

prev_month = month - 1 if month > 1 else 12
prev_year  = year  if month > 1 else year - 1

# ── 데이터 로드 ───────────────────────────────────────────
_META = {"id","user_id","year","month","created_at","updated_at","updated_by"}

def strip_meta(d: dict) -> dict:
    return {k: (v or 0) for k, v in d.items() if k not in _META} if d else {}

def get_confirmed_fields(raw: dict) -> list:
    if not raw: return []
    cf = raw.get("confirmed_fields")
    if cf is not None and isinstance(cf, list) and len(cf) > 0:
        return cf
    if raw.get("updated_by") == "시스템":
        return [k for k, v in raw.items() if isinstance(v, (int, float)) and k not in ("id", "year", "month", "user_id")]
    return []

def merge_data(curr_raw: dict, prev_raw: dict) -> tuple[dict, list]:
    curr = curr_raw or {}
    prev = prev_raw or {}
    cf = get_confirmed_fields(curr)
    res = {}
    all_keys = set(curr.keys()) | set(prev.keys())
    for k in all_keys:
        if k in ("id", "year", "month", "user_id", "updated_by", "updated_at", "created_at", "confirmed_fields"):
            continue
        if k in cf:
            res[k] = curr.get(k, 0)
        else:
            res[k] = prev.get(k, 0)
    return res, cf

# 현재 월 raw (수정자/시간 포함)
inc_raw   = get_monthly_income(year, month)
fixed_raw = get_fixed_costs(year, month)
util_raw  = get_utility_costs(year, month)
txns      = get_transactions(year, month)
invs      = get_investments(year, month)
other_incomes = get_other_incomes(year, month)

prev_inc_raw = get_monthly_income(prev_year, prev_month)
prev_fixed_raw = get_fixed_costs(prev_year, prev_month)
prev_util_raw = get_utility_costs(prev_year, prev_month)

inc, inc_cf = merge_data(inc_raw, prev_inc_raw)
fixed, fixed_cf = merge_data(fixed_raw, prev_fixed_raw)
util, util_cf = merge_data(util_raw, prev_util_raw)

# ── 수치 계산 ─────────────────────────────────────────────
def g(d, k): return int(d.get(k, 0) or 0)

jy_sal = g(inc,"junyoung_salary"); jy_bon = g(inc,"junyoung_bonus")
jd_sal = g(inc,"jiyun_salary");    jd_inc = g(inc,"jiyun_incentive")
other_inc = sum(item.get("amount", 0) for item in other_incomes)
jy_tot = jy_sal + jy_bon
jd_tot = jd_sal + jd_inc
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

elec = g(util,"electricity"); water = g(util,"water"); gas_v = g(util,"gas")
total_utility = elec + water + gas_v

cat_sum = {}
for t in txns:
    c = t.get("category","기타")
    cat_sum[c] = cat_sum.get(c,0) + t.get("amount",0)

living   = int(cat_sum.get("생활비",0))
snack    = int(cat_sum.get("간식비",0))
eating   = int(cat_sum.get("외식비",0))
culture  = int(cat_sum.get("문화비",0))
jy_lunch = int(cat_sum.get("준영점심",0))
medical  = int(cat_sum.get("의료비", 0)) # 의료비는 무조건 가계부 합산을 사용
gift     = int(cat_sum.get("경조비",0)) # 경조비도 무조건 가계부 합산을 사용
daily_total    = living + snack + eating + culture + jy_lunch
total_variable = total_utility + daily_total + medical + gift

investable    = livable - total_variable
actual_invest = sum(i.get("amount",0) for i in invs)
over_under    = investable - actual_invest

# ── 한눈에 보기 KPI 카드 ──────────────────────────────────
st.markdown("<p style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:8px;'>📊 이번 달 한눈에 보기</p>", unsafe_allow_html=True)

if total_income:
    inv_pct_val = investable / total_income * 100
    inv_pct_str = f"+{inv_pct_val:.1f}%" if inv_pct_val > 0 else f"{inv_pct_val:.1f}%"
else:
    inv_pct_str = ""
    
inv_delta_color = "#10b981" if investable >= 0 else "#ef4444"

fixed_pct = f"-{total_fixed/total_income*100:.1f}%" if total_income else ""
var_pct = f"-{total_variable/total_income*100:.1f}%" if total_income else ""

kpi_html = f"""<div style="display: flex; flex-direction: column; gap: clamp(8px, 2vw, 12px); margin-bottom: 20px;">
    <!-- 첫 번째 줄: 총 수입 -->
    <div style="width: 100%;">
        {_get_card_html("총 수입", f"₩{total_income:,.0f}", "", "#ff6b00")}
    </div>
    <!-- 두 번째 줄: 고정비 & 변동비 -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: clamp(8px, 2vw, 12px); width: 100%;">
        <div>{_get_card_html("고정비", f"₩{total_fixed:,.0f}", fixed_pct, "#1b263b", "#ef4444")}</div>
        <div>{_get_card_html("변동비", f"₩{total_variable:,.0f}", var_pct, "#94a3b8", "#ef4444")}</div>
    </div>
    <!-- 세 번째 줄: 익월 투자 가능 -->
    <div style="width: 100%;">
        {_get_card_html("익월 투자 가능", f"₩{investable:,.0f}", inv_pct_str, "#3b82f6", inv_delta_color)}
    </div>
</div>"""
st.markdown(kpi_html, unsafe_allow_html=True)
draw_neon_divider()

# ── 메타 포맷 함수 ────────────────────────────────────────
def meta_who(raw: dict, confirmed: bool) -> str:
    if not confirmed and not raw: return "<span class='meta'>(전월)</span>"
    by = (raw or {}).get("updated_by","") or ""
    if not by: return "<span class='meta'>-</span>"
    name = EMAIL_TO_NAME.get(by, by) if by else "-"
    return f"<span class='meta'>{name}</span>" 

def meta_when(raw: dict, confirmed: bool) -> str:
    if not confirmed: return "<span class='meta'>-</span>"
    at = (raw or {}).get("updated_at","") or ""
    if not at: return "<span class='meta'>-</span>"
    try:
        dt = datetime.fromisoformat(at.replace("Z","+00:00")) + timedelta(hours=9)
        return f"<span class='meta'>{dt.strftime('%m/%d %H:%M')}</span>"
    except:
        return f"<span class='meta'>{at[:10]}</span>"

def fmt_amt(val: int, confirmed: bool, cls: str = "amt-pos") -> str:
    if val == 0:
        if not confirmed:
            return "<span class='amt-dim'>-</span><span class='tag-unc'>예상</span>"
        return "<span class='amt-dim'>-</span>"
    
    txt = f"₩{val:,}"
    if not confirmed:
        return f"<span class='amt-unc'>{txt}</span><span class='tag-unc'>예상</span>"
    return f"<span class='{cls}'>{txt}</span>"

# ── 섹션 편집 상태 ────────────────────────────────────────
for _s in ("income", "fixed", "utility"):
    st.session_state.setdefault(f"edit_{_s}", False)

# ── 테이블 컬럼 비율 ──────────────────────────────────────
# 항목 박스 | 수정 버튼 | 확정 버튼 | 금액 박스
COL = [3.2, 1.2, 1.2, 4.4]

def get_columns(col_spec):
    try:
        return st.columns(col_spec, vertical_alignment="center")
    except TypeError:
        return st.columns(col_spec)

# ══════════════════════════════════════════════════════════
# ■ 렌더 헬퍼 (셀 단위 박스)
# ══════════════════════════════════════════════════════════

def _row_h1(label: str, val: int, confirmed: bool, who_html: str, when_html: str):
    st.markdown(f"<div class='fin-h1' style='margin-top:24px; display:flex; justify-content:space-between; width:100%; border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); background:#fff; padding:12px;'><span>📌 {label}</span><span>{fmt_amt(val, confirmed, 'amt-pos')}</span></div>", unsafe_allow_html=True)

def _row_h2(label: str, val: int, confirmed: bool):
    st.markdown(f"<div class='fin-h2' style='display:flex; justify-content:space-between; width:100%; margin-top:16px; margin-bottom:8px; border-radius:6px; background:#f8fafc; padding:8px 12px;'><span>▸ {label}</span><span>{fmt_amt(val, confirmed)}</span></div>", unsafe_allow_html=True)

def _edit_form(label: str, val: int, confirmed: bool, field_key: str, section_data: dict, cf_list: list, upsert_fn, step: int):
    """아코디언 인라인: 항목 금액 수정 및 확정 폼"""
    caption_html = "⚠️ 아직 확정되지 않은 예상 금액입니다." if not confirmed else "✅ 확정된 금액입니다."
    st.markdown(f"""
    <div style='margin-bottom: 12px;'>
        <div style='font-size:0.9rem; font-weight:700; color:#334155; margin-bottom:2px;'>✏️ {label}</div>
        <div style='font-size:0.75rem; color:#64748b;'>{caption_html}</div>
    </div>
    <hr style='margin: 0 0 12px 0; border: none; border-top: 1px dashed #e2e8f0;'>
    <div style='background:#f1f5f9; border-radius:8px; padding:10px 16px; margin-bottom:12px;'>
        <span style='font-size:0.75rem; color:#64748b; font-weight:600;'>현재 금액</span><br>
        <span style='font-size:1.4rem; font-weight:800; color:#1e293b; letter-spacing:0.02em;'>₩{val:,}</span>
    </div>
    """, unsafe_allow_html=True)

    new_val = st.number_input(
        "새 금액 (₩)",
        value=int(val),
        step=step,
        key=f"dlg_in_{field_key}",
        format="%d"
    )

    # 입력값 콤마 포함 미리보기
    if new_val != val:
        st.markdown(f"""
        <div style='background:#eff6ff; border-radius:6px; padding:6px 12px; margin-top:4px;'>
            <span style='font-size:0.75rem; color:#3b82f6; font-weight:600;'>변경 후: </span>
            <span style='font-size:1.1rem; font-weight:700; color:#1d4ed8;'>₩{int(new_val):,}</span>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    col_save, col_conf = st.columns(2)
    with col_save:
        if st.button("💾 저장", key=f"dlg_save_{field_key}", use_container_width=True, type="primary"):
            section_data[field_key] = new_val
            if upsert_fn(year, month, section_data, cf_list):
                st.rerun()
    with col_conf:
        if not confirmed:
            if st.button("✅ 확정", key=f"dlg_conf_{field_key}", use_container_width=True):
                section_data[field_key] = int(new_val or 0)
                if field_key not in cf_list:
                    cf_list.append(field_key)
                if upsert_fn(year, month, section_data, cf_list):
                    from utils.audio import play_notice_sound
                    play_notice_sound()
                    st.rerun()
        else:
            st.button("✔️ 확정 완료", key=f"dlg_conf_done_{field_key}", disabled=True, use_container_width=True)


def _row_item(label: str, val: int, confirmed: bool, field_key: str, section_data: dict, cf_list: list, upsert_fn, step: int = 10000):
    """카드 위쪽(항목정보) + 아래쪽(아코디언 방식의 폼) 구조"""
    cls       = "amt-pos" if confirmed else "amt-unc"
    check_tag = "" if confirmed else "<span class='tag-unc' style='font-size:0.6rem; margin-left:4px;'>예상</span>"

    # HTML 마크다운 (JS에서 onClick을 주입하므로 마크다운만 작성)
    st.markdown(f"""
    <div class='fin-row-container'>
        <span class='fin-row-label'>{label}</span>
        <span class='fin-row-amount'>
            <span class='{cls}'>₩{val:,}</span>{check_tag}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 아코디언 트리거 (투명한 헤더가 카드를 덮고 있어서 카드를 누르면 작동)
    with st.expander(" ", expanded=False):
        _edit_form(label, val, confirmed, field_key, section_data, cf_list, upsert_fn, step)

def _row_readonly(label: str, val: int):
    st.markdown(f"""
    <div class='fin-row-container'>
        <span class='fin-row-label'>{label}</span>
        <span class='fin-row-amount'>
            <span class='amt-pos'>₩{val:,}</span>
        </span>
    </div>
    """, unsafe_allow_html=True)

def _row_calc(label: str, val: int):
    """계산 결과 행 (녹색)"""
    cls = "amt-grn" if val >= 0 else "amt-neg"
    st.markdown(f"<div class='fin-calc' style='display:flex; justify-content:space-between; width:100%; border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); background:#ffffff; margin-top:24px; padding:12px;'><span>🔢 {label}</span><span class='{cls}'>₩{val:,}</span></div>", unsafe_allow_html=True)

def _row_invest(label: str, val: int, cls: str = "amt-yel"):
    """투자 행 (파란 배경)"""
    st.markdown(f"<div class='fin-inv' style='display:flex; justify-content:space-between; width:100%; border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); background:#ffffff; margin-top:24px; padding:12px;'><span>💡 {label}</span><span class='{cls}'>₩{val:,}</span></div>", unsafe_allow_html=True)

def _save_btn(section_key: str, label: str):
    """저장 버튼 행"""
    sc, _ = st.columns([2, 8])
    with sc:
        return st.button(f"💾 {label} 저장", key=f"save_{section_key}",
                         type="primary", use_container_width=True)

def _save_success(section_key: str):
    from utils.audio import play_notice_sound
    play_notice_sound()
    email = get_current_user_email()
    name  = EMAIL_TO_NAME.get(email, email)
    ts    = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    st.success(f"✅ {name} 수정 • {ts}")
    st.session_state[f"edit_{section_key}"] = False
    st.rerun()

def _other_income_item(year: int, month: int, other_incomes: list):
    label = "기타 수입 리스트"
    total_other = sum(item.get("amount", 0) for item in other_incomes)
    
    # 커스텀 카드 렌더링
    st.markdown(f"""
    <div class='fin-row-container'>
        <span class='fin-row-label'>{label}</span>
        <span class='fin-row-amount'>
            <span class='amt-pos'>₩{total_other:,}</span>
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander(" ", expanded=False):
        st.markdown(f"<p style='font-size:0.9rem; font-weight:700; color:#334155; margin-bottom:12px;'>✏️ {label}</p>", unsafe_allow_html=True)
        
        # 기존 내역
        if not other_incomes:
            st.caption("등록된 기타 수입이 없습니다.")
        else:
            for inc in other_incomes:
                col1, col2, col3 = st.columns([5, 4, 2], vertical_alignment="center")
                with col1:
                    st.markdown(f"<span style='font-size:0.85rem; color:#475569;'>{inc.get('description', '')}</span>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"<span style='font-size:0.9rem; font-weight:700; color:#1e293b;'>₩{inc.get('amount', 0):,}</span>", unsafe_allow_html=True)
                with col3:
                    if st.button("삭제", key=f"del_other_{inc['id']}", use_container_width=True):
                        delete_transaction(inc['id'])
                        st.rerun()
        
        st.markdown("<hr style='margin:16px 0; border:none; border-top:1px dashed #e2e8f0;'>", unsafe_allow_html=True)
        
        # 새 항목 추가
        with st.form("add_other_inc_form", clear_on_submit=True):
            st.markdown("<span style='font-size:0.8rem; font-weight:600; color:#64748b;'>새 기타 수입 추가</span>", unsafe_allow_html=True)
            new_desc = st.text_input("내용", placeholder="예: 당근마켓 판매, 명절 용돈 등", label_visibility="collapsed")
            new_amt = st.number_input("금액 (₩)", min_value=0, step=1000, label_visibility="collapsed")
            if st.form_submit_button("추가", use_container_width=True):
                if not new_desc:
                    st.error("내용을 입력해주세요.")
                elif new_amt <= 0:
                    st.error("금액을 0원 이상 입력해주세요.")
                else:
                    insert_transaction(year, month, 1, new_amt, new_desc, "기타 수입")
                    st.rerun()

# ══════════════════════════════════════════════════════════
# ■ 카드 렌더링 시작
# ══════════════════════════════════════════════════════════
draw_neon_divider()
st.write("")

# ─────────────────────────────────────────────────────────
# SECTION 1 : 수입
# ─────────────────────────────────────────────────────────
_row_h1(
    "총 가구 수입", total_income, set(["junyoung_salary","junyoung_bonus","jiyun_salary","jiyun_incentive","other_income"]).issubset(set(inc_cf)),
    meta_who(inc_raw, bool(inc_cf)),
    meta_when(inc_raw, bool(inc_cf))
)

jy_conf = set(["junyoung_salary","junyoung_bonus"]).issubset(set(inc_cf))
_row_h2("준영 수입", jy_tot, jy_conf)
_row_item("정기급여", jy_sal, "junyoung_salary" in inc_cf, "junyoung_salary", inc, inc_cf, upsert_monthly_income, 10000)
_row_item("상여금",   jy_bon, "junyoung_bonus"  in inc_cf, "junyoung_bonus",  inc, inc_cf, upsert_monthly_income, 10000)

jd_conf = set(["jiyun_salary","jiyun_incentive"]).issubset(set(inc_cf))
_row_h2("지윤 수입", jd_tot, jd_conf)
_row_item("정기급여",  jd_sal, "jiyun_salary"    in inc_cf, "jiyun_salary",    inc, inc_cf, upsert_monthly_income, 10000)
_row_item("인센티브",  jd_inc, "jiyun_incentive" in inc_cf, "jiyun_incentive", inc, inc_cf, upsert_monthly_income, 10000)

_row_h2("기타 수입", other_inc, True)
_other_income_item(year, month, other_incomes)

st.write("")

# ─────────────────────────────────────────────────────────
# SECTION 2 : 고정비
# ─────────────────────────────────────────────────────────
_row_h1(
    "고정비 (필수 유지비)", total_fixed, len(fixed_cf) >= 28,  # Total fixed items ~28
    meta_who(fixed_raw, bool(fixed_cf)),
    meta_when(fixed_raw, bool(fixed_cf))
)

FIXED_TREE = [
    ("주거비용", housing, [
        ("주담대 원리금","loan_payment",10000), ("관리비","maintenance_fee",10000), ("월세","rent",10000),
    ]),
    ("차량유지비", car_ins + g(fixed,"car_tax"), [
        ("자동차 보험","car_insurance",10000), ("운전자 보험","driver_insurance",10000),
        ("실비/건강보험","health_insurance",10000), ("암보험","cancer_insurance",10000),
        ("자동차세","car_tax",10000),
    ]),
    ("통신비", telecom, [
        ("준영 휴대폰","junyoung_phone",1000), ("지윤 휴대폰","jiyun_phone",1000), ("인터넷/TV","internet",1000),
    ]),
    ("교통비", transport, [
        ("준영 교통비","junyoung_transport",1000), ("지윤 교통비","jiyun_transport",1000),
        ("차량 주유비","fuel",1000), ("하이패스","hipass",1000),
    ]),
    ("기타 지출비", misc, [
        ("준영 모임통장","junyoung_club",10000), ("지윤 모임통장","jiyun_club",10000),
        ("준영 부모님 용돈","junyoung_parents",10000), ("지윤 부모님 용돈","jiyun_parents",10000),
    ]),
    ("구독 및 멤버십", subs, [
        ("쿠팡 와우","coupang",1000), ("유튜브","youtube",1000), ("네이버멤버십","naver",1000),
    ]),
    ("저축액", savings, [
        ("준영 희망적금","junyoung_savings1",10000), ("준영 주택청약","junyoung_savings2",10000),
        ("지윤 희망적금","jiyun_savings1",10000), ("지윤 주택청약","jiyun_savings2",10000),
    ]),
    ("개인 용돈", allowance, [
        ("준영 용돈","junyoung_allowance",10000), ("지윤 용돈","jiyun_allowance",10000),
    ]),
]

for grp_name, grp_total, grp_items in FIXED_TREE:
    grp_keys = set(fkey for _, fkey, _ in grp_items)
    grp_conf = grp_keys.issubset(set(fixed_cf))
    _row_h2(grp_name, grp_total, grp_conf)
    for lbl, fkey, fstep in grp_items:
        v = g(fixed, fkey)
        _row_item(lbl, v, fkey in fixed_cf, fkey, fixed, fixed_cf, upsert_fixed_costs, fstep)

st.write("")

# ─────────────────────────────────────────────────────────
# 생활 가능 총액
# ─────────────────────────────────────────────────────────
_row_calc("생활 가능 총액  =  총수입 − 고정비", livable)
st.write("")

# ─────────────────────────────────────────────────────────
# SECTION 3 : 변동비 (공과금 수정 가능, 나머지 읽기 전용)
# ─────────────────────────────────────────────────────────
_row_h1(
    "생활 비용 (변동비)", total_variable, True,
    meta_who(util_raw, bool(util_cf)),
    meta_when(util_raw, bool(util_cf))
)

util_keys = set(["electricity", "water", "gas"])
_row_h2("공과금", total_utility, util_keys.issubset(set(util_cf)))
_row_item("전기세", elec,  "electricity" in util_cf, "electricity", util, util_cf, upsert_utility_costs, 1000)
_row_item("수도세", water, "water"       in util_cf, "water",       util, util_cf, upsert_utility_costs, 1000)
_row_item("가스비", gas_v, "gas"         in util_cf, "gas",         util, util_cf, upsert_utility_costs, 1000)

# 생활지출
util_daily_keys = set(["living", "snack", "eating", "culture", "jy_lunch"])
_row_h2("생활지출 (가계부 자동연동)", daily_total, True)
_row_readonly("생활비",    living)
_row_readonly("간식비",    snack)
_row_readonly("외식비",    eating)
_row_readonly("문화비",    culture)
_row_readonly("준영 점심", jy_lunch)
st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

_row_h2("의료비 (가계부 자동연동)", medical, True)
_row_readonly("의료비", medical)
st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True) # expander를 안 쓰면 마진이 줄어들어 보정

_row_h2("경조/선물비 (가계부 자동연동)", gift, True)
_row_readonly("경조/선물비", gift)
st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

st.write("")

# ─────────────────────────────────────────────────────────
# 투자 가능액
# ─────────────────────────────────────────────────────────
_row_invest("익월 투자 가능 금액 = 생활가능 총액 - 변동비",
            investable, "amt-grn" if investable >= 0 else "amt-neg")

draw_neon_divider()

# ══════════════════════════════════════════════════════════
# ■ 한눈에 보기 KPI (위로 이동됨)
# ══════════════════════════════════════════════════════════


# ── 수정 이력 카드 ────────────────────────────────────────
def _hist_str(raw: dict | None, confirmed: bool) -> str | None:
    if not confirmed or not raw: return None
    by = raw.get("updated_by","") or ""
    at = raw.get("updated_at","") or ""
    if not by or not at: return None
    name = EMAIL_TO_NAME.get(by, by)
    try:
        dt = datetime.fromisoformat(at.replace("Z","+00:00")) + timedelta(hours=9)
        return f"{name} 수정 • {dt.strftime('%Y년 %m월 %d일 %H시 %M분')}"
    except:
        return f"{name} 수정 • {at[:16]}"

histories = [
    (sec, h) for sec, h in [
        ("💰 수입",   _hist_str(inc_raw,   bool(inc_cf))),
        ("🔒 고정비", _hist_str(fixed_raw, bool(fixed_cf))),
        ("⚡ 공과금", _hist_str(util_raw,  bool(util_cf))),
    ] if h
]

if histories:
    draw_neon_divider()
    rows_html = "".join(
        f"<div style='padding:4px 0;font-size:0.87rem;'>"
        f"<span style='color:#3b82f6;font-weight:600;display:inline-block;min-width:80px'>{s}</span>"
        f"&nbsp;&nbsp;<span style='color:#475569'>{h}</span></div>"
        for s, h in histories
    )
    st.markdown(f"""
    <div style='background:#f8fafc;border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,0.04);
                border-radius:12px;padding:14px 20px;'>
      <div style='font-size:0.74rem;color:#64748b;font-weight:600;
                  letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;'>
        &#128336; 수정 이력
      </div>
      {rows_html}
    </div>
    """, unsafe_allow_html=True)
