"""
utils/tips.py
탭 맨 위 한 줄 조언. 숫자는 앱이 계산하고(사실), 문장은 AI가 다듬는다.
먼저 앱이 만든 문장을 바로 보여 주고, 화면이 다 그려진 뒤 AI 문장으로 바꾼다.
AI 가 없거나 실패하면 앱이 만든 문장이 그대로 남는다. 읽기만 한다.
"""
import calendar
import hashlib
import html
import time

import streamlit as st

from utils import ai, check
from utils.fin import FIXED_FIELDS, FIXED_TREE, INCOME_FIELDS, UTILITY_FIELDS, unconfirmed_count

TABS = {"가계부", "대시보드", "재무현황", "투자현황"}
TABLE_TTL, FAIL_WAIT, MAX_AI_TIPS = 60, 300, 40


def _tables():
    from utils.auth import get_supabase_client
    c = st.session_state.get("_tip_tables")
    if not c or time.time() - c[0] > TABLE_TTL:
        c = (time.time(), check.load_tables(get_supabase_client()))
        st.session_state["_tip_tables"] = c
    return c[1]


def _pct(cur, prev):
    return f"{cur / prev * 100:.0f}%" if prev else None


def _w(v):
    return f"{int(v or 0):,}원"


def _diff(cur, prev):
    d = int(cur - prev)
    return "지난달과 같아요" if d == 0 else f"지난달보다 {abs(d):,}원 {'많아요' if d > 0 else '적어요'}"


def _month_numbers(tables, ym):
    row = lambda t: next((r for r in tables.get(t, []) if check._ym(r) == ym), {})
    inc, fixed, util = row("monthly_income"), row("fixed_costs"), row("utility_costs")
    cats, other = {}, 0
    for t in tables.get("transactions", []):
        if check._ym(t) != ym:
            continue
        if t.get("category") == check.OTHER_INCOME:
            other += t.get("amount") or 0
        else:
            c = t.get("category") or "기타"
            cats[c] = cats.get(c, 0) + (t.get("amount") or 0)
    invs = [r for r in tables.get("investments", []) if check._ym(r) == ym]
    n = {
        "income": sum((inc.get(f) or 0) for f in INCOME_FIELDS) + other,
        "fixed": sum((fixed.get(f) or 0) for f in FIXED_FIELDS),
        "utility": sum((util.get(f) or 0) for f in UTILITY_FIELDS),
        "variable": sum(cats.values()), "cats": cats,
        "groups": {g: sum((fixed.get(f) or 0) for _, f in items) for g, items in FIXED_TREE},
        "unconfirmed": unconfirmed_count(inc, fixed, util),
        "principal": sum((r.get("principal") or 0) for r in invs),
        "amount": sum((r.get("amount") or 0) for r in invs),
        "accounts": len(invs),
        "closed": ym in check.closed_months(tables),
    }
    n["expense"] = n["fixed"] + n["utility"] + n["variable"]
    n["net"] = n["income"] - n["expense"]
    return n


def make(tab: str, tables: dict, ym: tuple, now) -> tuple:
    """(앱이 만든 한 줄, AI 에게 줄 사실 글). 사실 글이 비면 AI 를 부르지 않는다."""
    today = (now.year, now.month)
    if ym > today:
        return "아직 오지 않은 달이에요.", ""
    cur, prev = _month_numbers(tables, ym), _month_numbers(tables, check._prev(ym))
    label = "이번 달" if ym == today else f"{ym[1]}월"
    facts = [f"보고 있는 달: {ym[0]}년 {ym[1]}월 ({'진행 중' if ym == today else '지난 달'}). '지난달'은 그 전달. 금액 단위 원."]
    if ym == today:
        days = calendar.monthrange(*ym)[1]
        facts.append(f"오늘은 {now.day}일, 이 달은 {days}일까지 ({now.day / days * 100:.0f}% 지남).")

    if tab == "가계부":
        if not cur["variable"]:
            return f"{label} 가계부에 입력된 지출이 아직 없어요.", ""
        facts.append(f"{label} 변동지출 합계 {_w(cur['variable'])}, 지난달 전체 {_w(prev['variable'])}"
                     + (f" (지난달의 {_pct(cur['variable'], prev['variable'])})" if prev["variable"] else ""))
        ranked = []
        for c, v in sorted(cur["cats"].items(), key=lambda x: -x[1]):
            p = prev["cats"].get(c, 0)
            facts.append(f"- {c}: {_w(v)}" + (f", 지난달 전체 {_w(p)}의 {_pct(v, p)}" if p else ", 지난달에는 없음"))
            if p >= 30_000:
                ranked.append((v / p, c))
        if not prev["variable"]:
            return f"{label} 변동지출은 {_w(cur['variable'])}입니다.", "\n".join(facts)
        line = f"{label} 변동지출은 지난달 전체의 {_pct(cur['variable'], prev['variable'])}예요."
        if ranked:
            r, c = max(ranked)
            line += f" {c}는 지난달의 {r * 100:.0f}%를 썼어요."
        return line, "\n".join(facts)

    if tab == "대시보드":
        if not (cur["income"] or cur["expense"]):
            return f"{label}에는 아직 입력된 수입·지출이 없어요.", ""
        facts += [f"{label}: 수입 {_w(cur['income'])}, 고정비 {_w(cur['fixed'])}, 공과금 {_w(cur['utility'])}, "
                  f"변동지출 {_w(cur['variable'])}, 남은 돈 {_w(cur['net'])}",
                  f"지난달: 수입 {_w(prev['income'])}, 고정비 {_w(prev['fixed'])}, 공과금 {_w(prev['utility'])}, "
                  f"변동지출 {_w(prev['variable'])}, 남은 돈 {_w(prev['net'])}",
                  f"아직 '예상' 상태(확정 안 함)인 재무 항목 {cur['unconfirmed']}개"]
        if cur["income"]:
            facts.append(f"지출은 수입의 {_pct(cur['expense'], cur['income'])}")
        line = f"{label} 남은 돈은 {_w(cur['net'])}" + (f", {_diff(cur['net'], prev['net'])}." if prev["income"] or prev["expense"] else "입니다.")
        return line, "\n".join(facts)

    if tab == "재무현황":
        if not (cur["income"] or cur["fixed"] or cur["utility"]):
            return f"{label} 재무현황에 저장된 값이 아직 없어요. 지금 보이는 금액은 지난달 값으로 채운 예상치예요.", ""
        facts += [f"{label}: 수입 {_w(cur['income'])}, 고정비 {_w(cur['fixed'])}, 공과금 {_w(cur['utility'])}",
                  f"지난달: 수입 {_w(prev['income'])}, 고정비 {_w(prev['fixed'])}, 공과금 {_w(prev['utility'])}",
                  f"아직 '예상' 상태(확정 안 함)인 항목 {cur['unconfirmed']}개"]
        facts += [f"- 고정비 {g}: {_w(v)} (지난달 {_w(prev['groups'].get(g, 0))})" for g, v in cur["groups"].items() if v or prev["groups"].get(g)]
        if cur["unconfirmed"]:
            return f"{label} '예상' 상태인 항목이 {cur['unconfirmed']}개 있어요. 금액이 맞으면 확정해 주세요.", "\n".join(facts)
        return f"{label} 고정비는 {_w(cur['fixed'])}, {_diff(cur['fixed'], prev['fixed'])}.", "\n".join(facts)

    if tab == "투자현황":
        if not cur["accounts"]:
            return f"{label} 투자현황에 입력된 계좌가 아직 없어요.", ""
        odd = [f["text"] for f in check.check_investments(tables, check.data_months(tables, today)) if f["ym"] == ym]
        rate = (cur["amount"] - cur["principal"]) / cur["principal"] * 100 if cur["principal"] else 0
        facts += [f"{label}: 계좌 {cur['accounts']}개, 원금 합계 {_w(cur['principal'])}, 평가액 합계 {_w(cur['amount'])}, 수익률 {rate:+.1f}%, "
                  f"{'마감됨' if cur['closed'] else '마감 안 함'}"]
        if prev["accounts"]:
            facts.append(f"지난달: 원금 합계 {_w(prev['principal'])}, 평가액 합계 {_w(prev['amount'])}")
        facts += ["앱이 찾은 확인할 값:"] + ([f"- {t}" for t in odd] or ["- 없음"])
        line = f"{label} 평가액은 {_w(cur['amount'])}, 원금 대비 {rate:+.1f}%예요."
        if odd:
            line += f" 확인해 볼 값이 {len(odd)}건 있어요 (AI 점검 탭)."
        elif ym < today and not cur["closed"]:
            line += " 아직 마감하지 않았어요."
        return line, "\n".join(facts)

    return "", ""


def _html(text: str, by_ai: bool) -> str:
    tag = "<span class='at-badge blue'>AI</span>" if by_ai else "<span class='at-badge'>요약</span>"
    return f"<div class='at-tip'>{tag}<span>{html.escape(text)}</span></div>"


def show(tab: str, ym: tuple, now):
    """페이지 머리말에서 부른다. 한 줄 자리를 만들고 지금 보여 줄 수 있는 문장을 넣는다."""
    if tab not in TABS:
        return
    try:
        line, facts = make(tab, _tables(), ym, now)
    except Exception:
        return                      # 조언 때문에 화면이 멈추면 안 된다
    if not line:
        return
    slot = st.empty()
    key = hashlib.sha1(f"{tab}|{ym}|{facts}".encode()).hexdigest()
    cached = st.session_state.setdefault("_tips", {}).get(key)
    slot.markdown(_html(cached or line, bool(cached)), unsafe_allow_html=True)
    if facts and not cached and ai.api_key():
        st.session_state["_tip_slot"] = (slot, tab, key, facts)


def fill():
    """화면이 다 그려진 뒤 진입점에서 부른다. AI 문장을 받아 한 줄을 바꾼다."""
    pending = st.session_state.pop("_tip_slot", None)
    if not pending:
        return
    slot, tab, key, facts = pending
    tips = st.session_state.setdefault("_tips", {})
    if time.time() < st.session_state.get("_tip_retry_at", 0) or st.session_state.get("_tip_calls", 0) >= MAX_AI_TIPS:
        return
    st.session_state["_tip_calls"] = st.session_state.get("_tip_calls", 0) + 1
    try:
        text = ai.one_line(tab, facts)
    except Exception:
        st.session_state["_tip_retry_at"] = time.time() + FAIL_WAIT   # 실패하면 한동안 다시 부르지 않는다
        return
    if text:
        if len(tips) > 60:
            tips.clear()
        tips[key] = text
        slot.markdown(_html(text, True), unsafe_allow_html=True)
