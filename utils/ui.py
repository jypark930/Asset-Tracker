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
    v = int(v or 0)
    return f"-₩{-v:,}" if v < 0 else f"₩{v:,}"


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
# 느낌: 어두운 회갈색 배경 위 반투명 유리 카드, 포인트는 파랑(강조)·초록(증가).
GLOBAL_CSS = """
<style>
:root {
  --at-glass: linear-gradient(160deg, rgba(255,255,255,0.09), rgba(255,255,255,0.03) 55%, rgba(59,130,246,0.06));
  --at-line: rgba(255,255,255,0.12);
  --at-text: #f3f4f6; --at-muted: #b4bac4; --at-faint: #a1a7b3;
  --at-green: #34d399; --at-red: #f87171;
  --at-radius: 22px;
}
/* 배경: 사진 대신 흐린 빛 번짐 */
.stApp {
  background:
    radial-gradient(1100px 620px at 12% -8%, rgba(150,128,108,0.35), transparent 60%),
    radial-gradient(900px 520px at 100% 18%, rgba(59,130,246,0.16), transparent 62%),
    radial-gradient(900px 700px at 45% 115%, rgba(120,104,94,0.32), transparent 60%),
    #1a191c;
  background-attachment: fixed;
}
header[data-testid="stHeader"] { background: rgba(26,25,28,0.55); backdrop-filter: blur(14px); }

.block-container { max-width: 1100px; padding-top: 3.2rem; padding-bottom: 4rem; }
#MainMenu, .stAppDeployButton { display: none !important; }

.at-title { font-size: 1.7rem; font-weight: 800; color: var(--at-text); text-align: center;
            letter-spacing: -0.5px; margin: 0.2rem 0 0.4rem; }
.at-month { font-size: 1.15rem; font-weight: 700; color: var(--at-text); min-width: 120px;
            text-align: center; line-height: 2.2rem; height: 2.2rem; margin: 0; }
.st-key-month_nav [data-testid="stMarkdownContainer"], .st-key-month_nav .stMarkdown { margin: 0 !important; }
.st-key-month_nav [data-testid="stElementContainer"] { display: flex; align-items: center; }
.st-key-month_nav { margin-bottom: 0.6rem; }
.st-key-month_nav button { min-height: 2.2rem; }

/* 유리 카드 공통 */
.at-kpi, .at-goal, .at-ring-card, div[style^="background: rgba(255, 255, 255, 0.06)"],
div[class*="st-key-glass"] {
  background: var(--at-glass) !important;
  -webkit-backdrop-filter: blur(18px) saturate(140%); backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid var(--at-line) !important; border-radius: var(--at-radius) !important;
  box-shadow: 0 10px 30px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.08);
}
div[class*="st-key-glass"] { padding: 1rem 1.1rem; }

/* 들어올 때: 흐릿하게 → 또렷하게, 차례로 */
@keyframes at-in { from { opacity: 0; transform: translateY(12px); filter: blur(8px); }
                   to   { opacity: 1; transform: none; filter: none; } }
.at-kpi, .at-goal, .at-ring-card, .at-cat, div[style^="background: rgba(255, 255, 255, 0.06)"], div[class*="st-key-glass"] {
  animation: at-in 0.7s cubic-bezier(.2,.7,.2,1) backwards;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.at-grid > :nth-child(2) { animation-delay: .06s; } .at-grid > :nth-child(3) { animation-delay: .12s; }
.at-grid > :nth-child(4) { animation-delay: .18s; } .at-grid > :nth-child(5) { animation-delay: .24s; }
.at-grid > :nth-child(6) { animation-delay: .30s; }
.at-cat:nth-child(2) { animation-delay: .05s; } .at-cat:nth-child(3) { animation-delay: .1s; }
.at-cat:nth-child(4) { animation-delay: .15s; } .at-cat:nth-child(n+5) { animation-delay: .2s; }
/* 마우스 올리면 살짝 떠오름 */
.at-kpi:hover, .at-ring-card:hover, div[style^="background: rgba(255, 255, 255, 0.06)"]:hover {
  transform: translateY(-5px); border-color: rgba(255,255,255,0.22) !important;
  box-shadow: 0 16px 36px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12);
}

/* 숫자 카드 */
.at-kpi { padding: 16px 16px 14px; height: 100%; }
.at-kpi .lbl { font-size: 0.8rem; color: var(--at-muted); font-weight: 700; }
.at-kpi .val { font-size: 1.45rem; font-weight: 800; color: var(--at-text); margin-top: 4px;
               letter-spacing: -0.5px; white-space: nowrap; }
.at-kpi .sub { font-size: 0.75rem; font-weight: 700; margin-top: 3px; color: var(--at-faint); }
.at-kpi.hl { background: linear-gradient(160deg, rgba(59,130,246,0.28), rgba(59,130,246,0.08) 60%, rgba(255,255,255,0.04)) !important;
             border-color: rgba(96,165,250,0.45) !important; }
.at-kpi.hl .val { color: #dbeafe; }
.at-kpi .up, .at-kpi .bad { color: var(--at-red); } .at-kpi .down, .at-kpi .good { color: var(--at-green); }
.at-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; margin: 4px 0 10px; }
@media (max-width: 640px) {
  .at-grid { grid-template-columns: repeat(2, minmax(0,1fr)); gap: 8px; }
  .at-grid > .at-kpi:last-child:nth-child(odd) { grid-column: 1 / -1; }
  .at-kpi .val { font-size: 1.12rem; }
  .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
}

/* 숫자 굴러 올라가기 (카운트업) */
.at-roll { display: inline-flex; align-items: flex-end; font-variant-numeric: tabular-nums; }
.at-roll > span { display: inline-block; height: 1.2em; line-height: 1.2em; }
.at-roll .rd { display: inline-block; height: 1.2em; line-height: 1.2em; overflow: hidden; vertical-align: bottom; }
.at-roll .rd > span { display: block; transform: translateY(calc(var(--d) * -1.2em));
                      animation: at-roll 1.1s cubic-bezier(.2,.7,.2,1) backwards; }
@keyframes at-roll { from { transform: translateY(0); } }

/* 원형 게이지 */
.at-ring-card { padding: 16px; display: flex; gap: 18px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
.at-ring { position: relative; width: 132px; height: 132px; flex: none; border-radius: 50%;
           box-shadow: 0 0 40px rgba(59,130,246,0.18); }
.at-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.at-ring .bg { stroke: rgba(255,255,255,0.08); }
.at-ring .fg { stroke: url(#at-ring-grad); stroke-linecap: round;
               stroke-dasharray: var(--c); stroke-dashoffset: var(--o);
               animation: at-ring 1.3s cubic-bezier(.2,.7,.2,1) backwards; }
@keyframes at-ring { from { stroke-dashoffset: var(--c); } }
.at-ring .mid { position: absolute; inset: 0; display: flex; flex-direction: column;
                align-items: center; justify-content: center; }
.at-ring .pct { font-size: 1.7rem; font-weight: 800; color: var(--at-text); letter-spacing: -1px; }
.at-ring .pct small { font-size: 0.8rem; color: var(--at-muted); margin-left: 1px; }
.at-ring .cap { font-size: 0.72rem; color: var(--at-muted); font-weight: 700; }
.at-ring-info { flex: 1; min-width: 130px; max-width: 460px; }
.at-ring-info .row { display: flex; justify-content: space-between; gap: 8px; font-size: 0.86rem;
                     color: #d1d5db; font-weight: 600; padding: 4px 0; }
.at-ring-info .row.dim { color: var(--at-faint); font-size: 0.78rem; }

/* 카테고리 막대 목록 */
.at-cat { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
.at-cat:last-child { border-bottom: none; }
.at-cat .name { width: 30%; font-size: 0.88rem; font-weight: 700; color: #e5e7eb; white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }
.at-cat .track { flex: 1; height: 8px; background: rgba(255,255,255,0.07); border-radius: 5px; overflow: hidden; }
.at-cat .track > div { height: 100%; border-radius: 5px; transform-origin: left;
                       background: linear-gradient(90deg, #2563eb, #60a5fa);
                       box-shadow: 0 0 10px rgba(59,130,246,0.55);
                       animation: at-grow 0.9s cubic-bezier(.2,.7,.2,1) backwards; }
@keyframes at-grow { from { transform: scaleX(0); } }
.at-cat .amt { width: 28%; text-align: right; font-size: 0.88rem; font-weight: 700; color: var(--at-text);
               white-space: nowrap; }
.at-cat .d { display: block; font-size: 0.7rem; font-weight: 700; }
.at-cat .d.up { color: var(--at-red); } .at-cat .d.down { color: var(--at-green); } .at-cat .d.same { color: var(--at-faint); }

/* Streamlit 기본 요소를 유리 느낌으로 */
div[data-testid="stExpander"] details { background: rgba(255,255,255,0.04); border-color: var(--at-line); border-radius: 16px; }
div[data-testid="stForm"] { background: rgba(255,255,255,0.04); border-color: var(--at-line); border-radius: var(--at-radius); }
.stButton button, .stFormSubmitButton button { transition: transform 0.2s ease, box-shadow 0.2s ease; }
.stButton button:hover, .stFormSubmitButton button:hover { transform: translateY(-2px); }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
  box-shadow: 0 0 18px rgba(59,130,246,0.45); }

/* 움직임 줄이기 설정을 켠 사람은 애니메이션 없음 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}

/* 잠긴 입력칸(설정 이름·이메일)도 잘 보이게 */
.stTextInput input:disabled { color: #e5e7eb !important; -webkit-text-fill-color: #e5e7eb !important; opacity: 1 !important; }

/* 투자현황 카드 묶음: 폰에서는 한 줄에 하나, 이름 왼쪽·금액 오른쪽 */
@media (max-width: 640px) {
  .at-inv-grid { grid-template-columns: 1fr !important; gap: 6px !important; }
  .at-inv-grid > div > div { flex-direction: row !important; flex-wrap: wrap; justify-content: space-between !important;
                             padding: 10px 14px !important; text-align: left !important; }
  .at-inv-grid > div > div > div { margin: 0 !important; font-size: 0.9rem !important; }
  .at-inv-grid > div > div > div:first-child { width: 4px !important; height: 18px !important; margin-right: 10px !important; }
  .at-inv-grid > div > div > div:nth-child(2) { flex: 1; }
  .at-inv-grid > div > div > div:last-child:nth-child(4) { width: 100%; text-align: right; font-size: 0.75rem !important; }
}

/* ── 큰 숫자 카드 (히어로) ── */
.at-hero { padding: 20px 22px; margin-bottom: 12px; }
.at-hero .lbl { font-size: 0.85rem; color: var(--at-muted); font-weight: 700; }
.at-hero .big { font-size: 2.3rem; font-weight: 800; color: var(--at-text); letter-spacing: -1px; line-height: 1.15; margin: 4px 0 2px; }
.at-hero .sub { font-size: 0.85rem; font-weight: 700; color: var(--at-faint); }
.at-hero .sub b { color: var(--at-text); }
@media (max-width: 640px) { .at-hero .big { font-size: 1.75rem; } .at-hero { padding: 16px; } }

/* ── 돈 흐름 막대 (수입이 어디로 갔나) ── */
.at-flow { display: flex; height: 18px; border-radius: 10px; overflow: hidden; background: rgba(255,255,255,0.07); margin: 14px 0 12px; }
.at-flow > div { height: 100%; transform-origin: left; animation: at-grow 0.9s cubic-bezier(.2,.7,.2,1) backwards; }
.at-flow > div + div { border-left: 2px solid rgba(26,25,28,0.8); }
/* 옆 칸과 바닥 높이 맞추기 */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .at-hero) { align-items: stretch; }
[data-testid="stColumn"]:has(.at-hero) > [data-testid="stVerticalBlock"] { height: 100%; }
[data-testid="stElementContainer"]:has(.at-hero) { flex: 1; }
[data-testid="stElementContainer"]:has(.at-hero) .stMarkdown,
[data-testid="stElementContainer"]:has(.at-hero) .stMarkdown > div,
[data-testid="stElementContainer"]:has(.at-hero) [data-testid="stMarkdownContainer"] { height: 100%; }
.at-hero { height: 100%; box-sizing: border-box; }
.at-legend { display: grid; grid-template-columns: repeat(auto-fit, minmax(112px, 1fr)); gap: 8px 14px; }
.at-legend .it { display: flex; flex-direction: column; gap: 1px; }
.at-legend .nm { font-size: 0.78rem; color: var(--at-muted); font-weight: 700; display: flex; align-items: center; gap: 6px; }
.at-legend .nm i { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }
.at-legend .v { font-size: 1.02rem; color: var(--at-text); font-weight: 800; white-space: nowrap; }
.at-legend .d { font-size: 0.72rem; font-weight: 700; color: var(--at-faint); white-space: nowrap; }
.at-legend .d.bad { color: var(--at-red); } .at-legend .d.good { color: var(--at-green); }

/* ── 알림 칩 (확인할 일) ── */
.at-todo { display: flex; align-items: center; gap: 10px; padding: 10px 14px; margin-bottom: 8px;
           border-radius: 14px; border: 1px solid rgba(251,191,36,0.35); background: rgba(251,191,36,0.08);
           color: #fde68a; font-size: 0.88rem; font-weight: 700; }
.at-todo.ok { border-color: rgba(52,211,153,0.35); background: rgba(52,211,153,0.08); color: #a7f3d0; }

/* ── 표 (가족·사람별 비교) ── */
.at-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.at-table th { color: var(--at-muted); font-weight: 700; font-size: 0.78rem; text-align: right; padding: 6px 8px;
               border-bottom: 1px solid var(--at-line); white-space: nowrap; }
.at-table th:first-child, .at-table td:first-child { text-align: left; }
.at-table td { padding: 9px 8px; text-align: right; color: var(--at-text); font-weight: 700; white-space: nowrap;
               border-bottom: 1px solid rgba(255,255,255,0.05); }
.at-table td:first-child { color: #d1d5db; font-weight: 600; }
.at-table tr.sep td { border-top: 1px solid var(--at-line); }
.at-table .up { color: var(--at-red); } .at-table .down { color: #60a5fa; } .at-table .dim { color: var(--at-faint); }
@media (max-width: 640px) { .at-table { font-size: 0.8rem; } .at-table td, .at-table th { padding: 7px 4px; } }

/* ── 상태 표시 ── */
.at-badge { display: inline-block; font-size: 0.72rem; font-weight: 800; padding: 2px 9px; border-radius: 99px;
            background: rgba(255,255,255,0.08); color: var(--at-muted); border: 1px solid var(--at-line); vertical-align: middle; }
.at-badge.warn { background: rgba(251,191,36,0.12); color: #fbbf24; border-color: rgba(251,191,36,0.35); }
.at-badge.ok { background: rgba(52,211,153,0.12); color: #34d399; border-color: rgba(52,211,153,0.35); }
.at-badge.blue { background: rgba(59,130,246,0.15); color: #93c5fd; border-color: rgba(96,165,250,0.4); }

/* 모바일: 선택 상자 누를 때 키보드가 뜨지 않게 */
div[data-testid="stSelectbox"] input { caret-color: transparent; }
</style>
"""


def inject_global_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", sub_cls: str = "", highlight: bool = False) -> str:
    cls = "at-kpi hl" if highlight else "at-kpi"
    sub_html = f"<div class='sub {sub_cls}'>{sub}</div>" if sub else "<div class='sub'>&nbsp;</div>"
    return f"<div class='{cls}'><div class='lbl'>{label}</div><div class='val'>{roll_number(value)}</div>{sub_html}</div>"


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


def roll_number(text: str) -> str:
    """숫자가 0에서 굴러 올라가는 표시 (CSS만 사용). 화면 읽기 프로그램에는 원래 글자를 준다."""
    import html as _h
    col = "<br>".join(str(i) for i in range(10))
    parts = []
    for ch in str(text):
        if ch.isdigit():
            parts.append(f"<span class='rd' aria-hidden='true'><span style='--d:{ch}'>{col}</span></span>")
        else:
            parts.append(f"<span aria-hidden='true'>{_h.escape(ch)}</span>")
    return f"<span class='at-roll' role='text' aria-label='{_h.escape(str(text))}'>{''.join(parts)}</span>"


def flow_bar(parts: list[tuple[str, int, str]], total: int) -> str:
    """수입(total)을 여러 몫으로 나눈 가로 막대. parts = [(이름, 금액, 색)]"""
    total = max(int(total or 0), sum(max(int(v or 0), 0) for _, v, _ in parts), 1)
    segs = "".join(
        f"<div title='{n}' style='width:{max(v, 0) / total * 100:.2f}%;background:{c};animation-delay:{i * 0.08:.2f}s'></div>"
        for i, (n, v, c) in enumerate(parts) if v and v > 0
    )
    return f"<div class='at-flow'>{segs}</div>"


def legend_item(name: str, value: str, color: str, sub: str = "", sub_cls: str = "", note: str = "") -> str:
    sub_html = f"<span class='d {sub_cls}'>{sub}</span>" if sub else ""
    if note:
        sub_html += f"<span class='d'>{note}</span>"
    return (f"<div class='it'><span class='nm'><i style='background:{color}'></i>{name}</span>"
            f"<span class='v'>{value}</span>{sub_html}</div>")


def ring_gauge(pct: float, caption: str = "달성") -> str:
    """원형 게이지 HTML. pct 는 0~100 (넘으면 원은 가득, 숫자는 그대로)."""
    r = 52
    c = 2 * 3.14159265 * r
    p = max(0.0, min(float(pct or 0), 100.0))
    o = c * (1 - p / 100)
    return (
        "<div class='at-ring'><svg viewBox='0 0 120 120'>"
        "<defs><linearGradient id='at-ring-grad' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0%' stop-color='#93c5fd'/><stop offset='100%' stop-color='#2563eb'/></linearGradient></defs>"
        f"<circle class='bg' cx='60' cy='60' r='{r}' fill='none' stroke-width='10'/>"
        f"<circle class='fg' cx='60' cy='60' r='{r}' fill='none' stroke-width='10' "
        f"style='--c:{c:.2f};--o:{o:.2f}'/></svg>"
        f"<div class='mid'><div class='pct'>{float(pct or 0):.0f}<small>%</small></div>"
        f"<div class='cap'>{caption}</div></div></div>"
    )
