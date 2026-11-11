"""
utils/ui.py
화면 공통 요소: 한국 시간, 월 이동, 페이지 머리말, 금액 표시, 공통 스타일
"""
from datetime import datetime, timedelta, timezone

import streamlit as st

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """서버 시간대와 상관없이 한국 시간을 돌려준다."""
    return datetime.now(KST).replace(tzinfo=None)


# ── 금액 표시 ─────────────────────────────────────────────
def won(v) -> str:
    return f"₩{int(v or 0):,}"


def won_short(v) -> str:
    """큰 금액을 짧게: 1,234만 / 1.2억"""
    v = int(v or 0)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 100_000_000:
        return f"{sign}{a / 100_000_000:.2f}억"
    if a >= 10_000:
        return f"{sign}{a / 10_000:,.0f}만"
    return f"{sign}{a:,}"


# ── 월 상태 ──────────────────────────────────────────────
def _ensure_month():
    if "global_year" not in st.session_state or "global_month" not in st.session_state:
        n = now_kst()
        st.session_state.global_year = n.year
        st.session_state.global_month = n.month


def current_month() -> tuple[int, int]:
    _ensure_month()
    return st.session_state.global_year, st.session_state.global_month


def prev_of(year: int, month: int) -> tuple[int, int]:
    return (year, month - 1) if month > 1 else (year - 1, 12)


def _shift(delta: int):
    y, m = st.session_state.global_year, st.session_state.global_month
    idx = y * 12 + (m - 1) + delta
    st.session_state.global_year, st.session_state.global_month = divmod(idx, 12)
    st.session_state.global_month += 1


def _go_today():
    n = now_kst()
    st.session_state.global_year, st.session_state.global_month = n.year, n.month


def flash(msg: str, icon: str = ":material/check_circle:"):
    """다음 화면 그리기 때 한 번 보여 줄 알림 (st.rerun 뒤에도 보이게)"""
    st.session_state["_flash"] = (msg, icon)


def _show_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        st.toast(f[0], icon=f[1])


def page_header(title: str, caption: str | None = None, show_month: bool = True) -> tuple[int, int]:
    """페이지 제목 + 월 이동 막대. 선택된 (연, 월)을 돌려준다."""
    _show_flash()
    year, month = current_month()
    st.markdown(f"<div class='at-title'>{title}</div>", unsafe_allow_html=True)
    if caption:
        st.caption(caption)
    if show_month:
        n = now_kst()
        is_now = (year, month) == (n.year, n.month)
        with st.container(horizontal=True, horizontal_alignment="center",
                          vertical_alignment="center", key="month_nav"):
            st.button("", icon=":material/chevron_left:", key="nav_prev",
                      on_click=_shift, args=(-1,), help="이전 달")
            st.markdown(f"<div class='at-month'>{year}년 {month}월</div>", unsafe_allow_html=True)
            st.button("", icon=":material/chevron_right:", key="nav_next",
                      on_click=_shift, args=(1,), help="다음 달")
            if not is_now:
                st.button("이번 달", key="nav_today", on_click=_go_today, type="tertiary")
    return year, month


def section(title: str, icon: str | None = None):
    label = f":material/{icon}: {title}" if icon else title
    st.markdown(f"#### {label}")


# ── 공통 스타일 ───────────────────────────────────────────
# 테마 색·글꼴은 .streamlit/config.toml 에 있다. 여기에는 테마로 못 하는 것만 둔다.
GLOBAL_CSS = """
<style>
.block-container { max-width: 1100px; padding-top: 3.2rem; padding-bottom: 4rem; }
#MainMenu, .stAppDeployButton { display: none !important; }

.at-title { font-size: 1.6rem; font-weight: 800; color: #0f172a; text-align: center;
            letter-spacing: -0.5px; margin: 0.2rem 0 0.4rem; }
.at-month { font-size: 1.15rem; font-weight: 700; color: #0f172a; min-width: 120px;
            text-align: center; }
.st-key-month_nav { margin-bottom: 0.6rem; }
.st-key-month_nav button { min-height: 2.2rem; }

/* 숫자 카드 */
.at-kpi { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:14px 14px 12px;
          height:100%; }
.at-kpi .lbl { font-size:0.8rem; color:#64748b; font-weight:700; }
.at-kpi .val { font-size:1.3rem; font-weight:800; color:#0f172a; margin-top:2px;
               letter-spacing:-0.5px; white-space:nowrap; }
.at-kpi .sub { font-size:0.75rem; font-weight:700; margin-top:2px; color:#94a3b8; }
.at-kpi.hl { background:#fff7ed; border-color:#fed7aa; }
.at-kpi.hl .val { color:#c2410c; }
.at-kpi .up { color:#dc2626; } .at-kpi .down { color:#16a34a; }
.at-kpi .good { color:#16a34a; } .at-kpi .bad { color:#dc2626; }
.at-grid { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:10px; margin: 4px 0 8px; }
@media (max-width: 640px) {
  .at-grid { grid-template-columns: repeat(2, minmax(0,1fr)); gap:8px; }
  .at-kpi .val { font-size:1.1rem; }
  .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
}

/* 진행 막대 */
.at-goal { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:14px; }
.at-goal .row { display:flex; justify-content:space-between; font-size:0.85rem; color:#475569;
                font-weight:600; margin-top:6px; }
.at-goal .bar { height:10px; background:#f1f5f9; border-radius:6px; overflow:hidden; margin-top:8px; }
.at-goal .bar > div { height:100%; background:#ff6b00; border-radius:6px; }

/* 카테고리 막대 목록 */
.at-cat { display:flex; align-items:center; gap:10px; padding:7px 0; border-bottom:1px solid #f1f5f9; }
.at-cat:last-child { border-bottom:none; }
.at-cat .name { width:30%; font-size:0.88rem; font-weight:700; color:#334155; white-space:nowrap;
                overflow:hidden; text-overflow:ellipsis; }
.at-cat .track { flex:1; height:8px; background:#f1f5f9; border-radius:5px; overflow:hidden; }
.at-cat .track > div { height:100%; background:#ff6b00; border-radius:5px; }
.at-cat .amt { width:28%; text-align:right; font-size:0.88rem; font-weight:700; color:#0f172a;
               white-space:nowrap; }
.at-cat .d { display:block; font-size:0.7rem; font-weight:700; }
.at-cat .d.up { color:#dc2626; } .at-cat .d.down { color:#16a34a; } .at-cat .d.same { color:#94a3b8; }

/* 모바일: 선택 상자 누를 때 키보드가 뜨지 않게 */
div[data-testid="stSelectbox"] input { caret-color: transparent; }
</style>
"""


def inject_global_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", sub_cls: str = "", highlight: bool = False) -> str:
    cls = "at-kpi hl" if highlight else "at-kpi"
    sub_html = f"<div class='sub {sub_cls}'>{sub}</div>" if sub else "<div class='sub'>&nbsp;</div>"
    return f"<div class='{cls}'><div class='lbl'>{label}</div><div class='val'>{value}</div>{sub_html}</div>"


def kpi_grid(cards: list[str]):
    st.markdown("<div class='at-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def delta_text(curr: int, prev: int, more_is_bad: bool = True) -> tuple[str, str]:
    """전월 대비 문구와 색 클래스"""
    d = int(curr or 0) - int(prev or 0)
    if d == 0:
        return "전월과 같음", ""
    arrow = "▲" if d > 0 else "▼"
    bad = (d > 0) == more_is_bad
    return f"전월 대비 {arrow} {won_short(abs(d))}", ("bad" if bad else "good")
