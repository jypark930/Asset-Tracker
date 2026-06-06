"""
pages/5_📋_재무현황.py  ─  수입/지출 구조 종합 현황
항목/금액/수정자/수정일 테이블 | 섹션별 인라인 수정 | 전월 자동 불러오기
"""
import streamlit as st
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
)

if not is_authenticated():
    if not try_restore_session():
        st.warning("🔒 로그인이 필요합니다.")
        st.switch_page("app.py")

now = datetime.now()

# ══════════════════════════════════════════════════════════
# ■ CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

.fin-h1 {
    background: rgba(124,58,237,0.22);
    border-left: 4px solid #7c3aed;
    padding: 9px 14px;
    border-radius: 5px;
    font-weight: 700;
    font-size: 0.94rem;
}
.fin-h2 {
    background: rgba(255,255,255,0.045);
    border-left: 3px solid rgba(167,139,250,0.45);
    padding: 7px 14px 7px 22px;
    border-radius: 3px;
    font-weight: 600;
    font-size: 0.87rem;
}
.fin-h3 {
    padding: 5px 0 5px 40px;
    font-size: 0.84rem;
    color: rgba(255,255,255,0.70);
    border-bottom: 1px solid rgba(255,255,255,0.035);
}
.fin-calc {
    background: rgba(52,211,153,0.13);
    border-left: 4px solid #34d399;
    padding: 9px 14px;
    font-weight: 700;
    font-size: 0.94rem;
    border-radius: 5px;
}
.fin-inv {
    background: rgba(96,165,250,0.13);
    border-left: 4px solid #60a5fa;
    padding: 9px 14px;
    font-weight: 700;
    border-radius: 5px;
}
.tbl-hdr {
    font-size: 0.76rem;
    font-weight: 600;
    color: rgba(255,255,255,0.42);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding-bottom: 6px;
    border-bottom: 2px solid rgba(167,139,250,0.35);
}
.amt-pos  { color:#60a5fa; font-family:'Courier New',monospace; font-weight:600; }
.amt-neg  { color:#f87171; font-family:'Courier New',monospace; font-weight:600; }
.amt-grn  { color:#34d399; font-family:'Courier New',monospace; font-weight:700; }
.amt-yel  { color:#fbbf24; font-family:'Courier New',monospace; font-weight:600; }
.amt-dim  { color:rgba(255,255,255,0.28); }
.amt-unc  { color:#fbbf24; font-family:'Courier New',monospace; }
.meta     { color:rgba(255,255,255,0.48); font-size:0.82rem; }
.tag-unc  { background:rgba(251,191,36,0.18); color:#fbbf24; font-size:0.72rem;
            padding:1px 6px; border-radius:10px; font-weight:600; margin-left:4px; }
</style>
""", unsafe_allow_html=True)

st.title("📋 수입 · 지출 재무 현황")
st.caption("항목별 수정 가능 | 미입력 항목은 전월 데이터 자동 적용 후 (미확정) 표시")

# ── 월 선택 ──────────────────────────────────────────────
cy, cm, _ = st.columns([1, 1, 7])
with cy:
    year  = st.selectbox("연도", [2025, 2026, 2027], index=1, key="fin_year")
with cm:
    month = st.selectbox("월", list(range(1, 13)), index=now.month - 1, key="fin_month")

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
        if k in ("id", "year", "month", "user_id", "updated_by", "updated_at", "confirmed_fields"):
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
jy_tot = jy_sal + jy_bon
jd_tot = jd_sal + jd_inc
total_income = jy_tot + jd_tot

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

living   = cat_sum.get("생활비",0); snack   = cat_sum.get("간식비",0)
eating   = cat_sum.get("외식비",0); culture = cat_sum.get("문화비",0)
jy_lunch = cat_sum.get("준영점심",0); medical = cat_sum.get("의료비",0)
gift     = cat_sum.get("경조비",0)
daily_total    = living + snack + eating + culture + jy_lunch
total_variable = total_utility + daily_total + medical + gift

investable    = livable - total_variable
actual_invest = sum(i.get("amount",0) for i in invs)
over_under    = investable - actual_invest

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
# 항목 | 금액 | 수정자 | 수정일 | 수정버튼
COL = [5.2, 2.2, 1.5, 2.2, 1.4]

# ══════════════════════════════════════════════════════════
# ■ 렌더 헬퍼
# ══════════════════════════════════════════════════════════

def _table_header():
    c = st.columns(COL)
    for col, lb in zip(c, ["항목","금액","수정자","수정일","&nbsp;"]):
        col.markdown(f"<div class='tbl-hdr'>{lb}</div>", unsafe_allow_html=True)

def _row_h1(label: str, val: int, confirmed: bool, who_html: str, when_html: str):
    c = st.columns(COL)
    c[0].markdown(f"<div class='fin-h1'>📌 {label}</div>", unsafe_allow_html=True)
    c[1].markdown(fmt_amt(val, confirmed, "amt-pos"), unsafe_allow_html=True)
    c[2].markdown(who_html,  unsafe_allow_html=True)
    c[3].markdown(when_html, unsafe_allow_html=True)
    c[4].markdown("")

def _row_h2(label: str, val: int, confirmed: bool):
    c = st.columns(COL)
    c[0].markdown(f"<div class='fin-h2'>▸ {label}</div>", unsafe_allow_html=True)
    c[1].markdown(fmt_amt(val, confirmed), unsafe_allow_html=True)

def _row_item(label: str, val: int, confirmed: bool, field_key: str, section_data: dict, cf_list: list, upsert_fn, step: int = 10000):
    c = st.columns(COL)
    c[0].markdown(f"<div class='fin-h3'>{label}</div>", unsafe_allow_html=True)
    in_edit = st.session_state.get(f"edit_{field_key}", False)
    
    if in_edit:
        with c[1]:
            new_val = st.number_input(label, min_value=0, value=int(val or 0), step=step, key=f"inp_{field_key}", label_visibility="collapsed", format="%d")
            st.caption(f"₩{new_val:,}" if new_val else "₩0")
        c[2].markdown("")
        c[3].markdown("")
        with c[4]:
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("💾", key=f"save_{field_key}", help="저장"):
                section_data[field_key] = new_val
                if field_key not in cf_list:
                    cf_list.append(field_key)
                if upsert_fn(year, month, section_data, cf_list):
                    from utils.audio import play_notice_sound
                    play_notice_sound()
                    st.session_state[f"edit_{field_key}"] = False
                    st.rerun()
            if col_btn2.button("❌", key=f"cancel_{field_key}", help="취소"):
                st.session_state[f"edit_{field_key}"] = False
                st.rerun()
    else:
        c[1].markdown(fmt_amt(val, confirmed), unsafe_allow_html=True)
        c[2].markdown("")
        c[3].markdown("")
        with c[4]:
            if st.button("✏️", key=f"editbtn_{field_key}", help="수정"):
                st.session_state[f"edit_{field_key}"] = True
                st.rerun()

def _row_calc(label: str, val: int):
    """계산 결과 행 (녹색)"""
    c = st.columns(COL)
    cls = "amt-grn" if val >= 0 else "amt-neg"
    c[0].markdown(f"<div class='fin-calc'>🔢 {label}</div>", unsafe_allow_html=True)
    c[1].markdown(f"<span class='{cls}'>₩{val:,}</span>", unsafe_allow_html=True)
    for i in (2,3,4): c[i].markdown("")

def _row_invest(label: str, val: int, cls: str = "amt-yel"):
    """투자 행 (파란 배경)"""
    c = st.columns(COL)
    c[0].markdown(f"<div class='fin-inv'>💡 {label}</div>", unsafe_allow_html=True)
    c[1].markdown(f"<span class='{cls}'>₩{val:,}</span>", unsafe_allow_html=True)
    for i in (2,3,4): c[i].markdown("")

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

# ══════════════════════════════════════════════════════════
# ■ 테이블 렌더링 시작
# ══════════════════════════════════════════════════════════
st.divider()
_table_header()
st.write("")

# ─────────────────────────────────────────────────────────
# SECTION 1 : 수입
# ─────────────────────────────────────────────────────────
_row_h1(
    "총 가구 수입", total_income, set(["junyoung_salary","junyoung_bonus","jiyun_salary","jiyun_incentive"]).issubset(set(inc_cf)),
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

# 생활지출 (읽기 전용 — 가계부 탭에서 입력)
_row_h2("생활지출", daily_total, True)
_row_item_view("생활비",    living,   True)
_row_item_view("간식비",    snack,    True)
_row_item_view("외식비",    eating,   True)
_row_item_view("문화비",    culture,  True)
_row_item_view("준영 점심", jy_lunch, True)

_row_h2("의료비",     medical, True)
_row_h2("경조/선물비", gift,   True)

st.write("")

# ─────────────────────────────────────────────────────────
# 투자 가능액 / 실제 투자액
# ─────────────────────────────────────────────────────────
_row_invest("투자 가능액  =  생활가능 − 변동비",
            investable, "amt-grn" if investable >= 0 else "amt-neg")
_row_invest("실제 투자액", actual_invest, "amt-yel")

over_label = "✅ 여유 투자금" if over_under >= 0 else "⚠️ 투자 초과금"
over_cls   = "amt-grn"       if over_under >= 0 else "amt-neg"
c = st.columns(COL)
c[0].markdown(f"<div class='fin-inv'>{over_label}</div>", unsafe_allow_html=True)
c[1].markdown(f"<span class='{over_cls}'>₩{abs(over_under):,}</span>", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════
# ■ 한눈에 보기 KPI
# ══════════════════════════════════════════════════════════
st.subheader("📊 한눈에 보기")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💰 총 수입",     f"₩{total_income:,}")
k2.metric("🔒 고정비",      f"₩{total_fixed:,}",
          delta=f"-{total_fixed/total_income*100:.1f}%" if total_income else None,
          delta_color="inverse")
k3.metric("🛒 변동비",      f"₩{total_variable:,}",
          delta=f"-{total_variable/total_income*100:.1f}%" if total_income else None,
          delta_color="inverse")
k4.metric("💡 투자 가능액", f"₩{investable:,}",
          delta="흑자" if investable >= 0 else "적자",
          delta_color="normal" if investable >= 0 else "inverse")
k5.metric("📈 실제 투자액", f"₩{actual_invest:,}")

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
    st.divider()
    rows_html = "".join(
        f"<div style='padding:4px 0;font-size:0.87rem;'>"
        f"<span style='color:#a78bfa;font-weight:600;display:inline-block;min-width:80px'>{s}</span>"
        f"&nbsp;&nbsp;<span style='color:rgba(255,255,255,0.52)'>{h}</span></div>"
        for s, h in histories
    )
    st.markdown(f"""
    <div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
                border-radius:12px;padding:14px 20px;'>
      <div style='font-size:0.74rem;color:rgba(255,255,255,0.38);font-weight:600;
                  letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;'>
        &#128336; 수정 이력
      </div>
      {rows_html}
    </div>
    """, unsafe_allow_html=True)
