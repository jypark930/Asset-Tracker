"""
utils/check.py
입력값 점검: 이상해 보이는 값, 입력 안 된 곳을 규칙으로 찾는다 (AI 없이 계산).
AI 에게 넘길 월별 요약 글도 여기서 만든다. 읽기만 하고 DB 에 쓰지 않는다.
"""
from statistics import median

from utils.fin import (
    INCOME_ITEMS, FIXED_TREE, UTILITY_ITEMS, INCOME_FIELDS, confirmed_fields, unconfirmed_count,
)

TABLES = ["transactions", "monthly_income", "fixed_costs", "utility_costs", "investments", "monthly_goals"]
OTHER_INCOME = "기타 수입"

# 급변으로 보는 기준: 전달 대비 30% 이상이면서 50만원 이상, 그리고 그 계좌 평소 변동의 3배 초과
JUMP_RATE, JUMP_MIN, JUMP_VS_USUAL = 0.3, 500_000, 3


def load_tables(client) -> dict:
    """로그인한 사람이 볼 수 있는 행을 표마다 한 번에 읽는다 (1000행씩 나눠 받기)."""
    out = {}
    for t in TABLES:
        rows, start = [], 0
        while True:
            part = client.table(t).select("*").range(start, start + 999).execute().data or []
            rows += part
            if len(part) < 1000:
                break
            start += 1000
        out[t] = rows
    return out


# ── 달 계산 ───────────────────────────────────────────────
def _ym(r):
    return (r.get("year"), r.get("month"))


def _prev(ym):
    y, m = ym
    return (y, m - 1) if m > 1 else (y - 1, 12)


def months_between(start, end) -> list:
    out, (y, m) = [], start
    while (y, m) <= end:
        out.append((y, m))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


def data_months(tables: dict, today: tuple) -> list:
    """자료가 있는 첫 달부터 이번 달까지"""
    yms = [_ym(r) for t in TABLES for r in tables.get(t, [])
           if isinstance(r.get("year"), int) and isinstance(r.get("month"), int)]
    yms = [x for x in yms if x <= today]
    return months_between(min(yms), today) if yms else []


def _label(ym):
    return f"{ym[0]}년 {ym[1]}월"


def _n(v):
    return f"{int(v or 0):,}원"


def _finding(kind, area, ym, text):
    return {"kind": kind, "area": area, "ym": ym, "text": f"{_label(ym)} {text}"}


# ── 투자현황 ──────────────────────────────────────────────
def _inv_series(tables):
    """(소유자, 계좌) → {달: (원금, 평가액)}, 그리고 같은 달에 두 번 들어간 계좌 목록"""
    series, dup = {}, []
    for r in tables.get("investments", []):
        key = (r.get("owner") or "?", r.get("account_type") or "?")
        ym = _ym(r)
        if ym in series.setdefault(key, {}):
            dup.append((key, ym))
        series[key][ym] = (r.get("principal") or 0, r.get("amount") or 0)
    return series, dup


def _jump(prev, cur, usual):
    """전달 → 이번 달 변화가 이상한지. 이상하면 설명 글, 아니면 None"""
    if prev <= 0 or cur <= 0:
        return None
    ratio = cur / prev
    if 8 <= ratio <= 12 or 1 / 12 <= ratio <= 1 / 8:
        return f"{_n(prev)} → {_n(cur)} (약 {'10배' if ratio > 1 else '10분의 1'}, 자릿수 실수일 수 있음)"
    diff = cur - prev
    if abs(diff) >= JUMP_MIN and abs(diff) >= JUMP_RATE * prev and (usual is None or abs(diff) > JUMP_VS_USUAL * usual):
        return f"{_n(prev)} → {_n(cur)} ({diff / prev * 100:+.0f}%)"
    return None


def check_investments(tables: dict, months: list) -> list:
    out = []
    series, dup = _inv_series(tables)
    month_has_rows = {ym for s in series.values() for ym in s}

    for key, ym in dup:
        if ym in months:
            out.append(_finding("odd", "투자현황", ym, f"{key[0]} / {key[1]} 계좌가 두 번 들어가 있습니다."))

    stale = {}   # 달 → 전달과 값이 같은 계좌
    for key, s in sorted(series.items()):
        name = f"{key[0]} / {key[1]}"
        yms = sorted(s)
        dormant = len({s[x] for x in yms}) == 1        # 한 번도 안 바뀐 계좌는 '안 고침' 으로 보지 않는다
        steps = [(s[_prev(x)], s[x]) for x in yms if _prev(x) in s]
        usual = []
        for i in (0, 1):
            d = [abs(c[i] - p[i]) for p, c in steps]
            usual.append(median(d) if len(d) >= 3 else None)

        for ym in months:
            cur, prev = s.get(ym), s.get(_prev(ym))
            if cur is None:
                if prev is not None and ym in month_has_rows:
                    out.append(_finding("odd", "투자현황", ym, f"{name} 계좌가 빠져 있습니다 (전달에는 {_n(prev[0])})."))
                continue
            if prev is None:
                continue
            if (prev[0] > 0 or prev[1] > 0) and cur[0] == 0 and cur[1] == 0:
                out.append(_finding("odd", "투자현황", ym, f"{name} 금액이 0원이 됐습니다 (전달 원금 {_n(prev[0])})."))
                continue
            j = _jump(prev[0], cur[0], usual[0])
            if j:
                out.append(_finding("odd", "투자현황", ym, f"{name} 원금 {j}"))
            else:
                j = _jump(prev[1], cur[1], usual[1])
                if j:
                    out.append(_finding("odd", "투자현황", ym, f"{name} 평가액 {j}"))
            if cur == prev and not dormant:
                stale.setdefault(ym, []).append(name)

        # 평가액이 원금과 너무 다름: 계좌마다 가장 최근 달 한 번만
        last = [x for x in yms if x in months]
        if last:
            p, a = s[last[-1]]
            if p > 0 and a > 0 and not (0.3 <= a / p <= 3):
                out.append(_finding("odd", "투자현황", last[-1],
                                    f"{name} 평가액({_n(a)})이 원금({_n(p)})의 {a / p:.1f}배입니다."))

    for ym, names in sorted(stale.items()):
        total = sum(1 for s in series.values() if ym in s)
        if len(names) == total:
            text = f"투자현황 {total}개 계좌가 모두 전달 값 그대로입니다 (복사만 되고 입력 안 한 것 같음)."
        else:
            text = f"투자현황에서 전달과 값이 같은 계좌 {len(names)}개: {', '.join(names)}"
        out.append(_finding("missing", "투자현황", ym, text))
    return out


# ── 입력 안 된 곳 ─────────────────────────────────────────
def _by_month(rows):
    return {_ym(r): r for r in rows}


def closed_months(tables) -> set:
    return {_ym(r) for r in tables.get("monthly_income", []) if "investments_closed" in (r.get("confirmed_fields") or [])}


def check_missing(tables: dict, months: list, today: tuple) -> list:
    out = []
    inc, fixed, util = (_by_month(tables.get(t, [])) for t in ("monthly_income", "fixed_costs", "utility_costs"))
    closed = closed_months(tables)
    inv_months = {_ym(r) for r in tables.get("investments", [])}
    tx_count = {}
    for t in tables.get("transactions", []):
        if t.get("category") != OTHER_INCOME:
            tx_count[_ym(t)] = tx_count.get(_ym(t), 0) + 1
    past_counts = [tx_count[m] for m in months if m < today and tx_count.get(m)]
    usual_tx = median(past_counts) if past_counts else 0

    for ym in months:
        past = ym < today
        # 가계부
        n = tx_count.get(ym, 0)
        if n == 0:
            out.append(_finding("missing", "가계부", ym, "가계부에 입력된 지출이 없습니다."))
        elif past and usual_tx >= 10 and n < 0.4 * usual_tx:
            out.append(_finding("missing", "가계부", ym, f"가계부 지출이 {n}건뿐입니다 (보통 {usual_tx:.0f}건)."))
        # 재무현황
        blank = []
        if not sum((inc.get(ym, {}).get(f) or 0) for f in INCOME_FIELDS):
            blank.append("수입")
        if ym not in fixed:
            blank.append("고정비")
        if ym not in util:
            blank.append("공과금")
        if blank:
            out.append(_finding("missing", "재무현황", ym, f"재무현황에 {'·'.join(blank)} 입력이 없습니다."))
        elif past:
            u = unconfirmed_count(inc.get(ym, {}), fixed.get(ym, {}), util.get(ym, {}))
            if u:
                out.append(_finding("missing", "재무현황", ym, f"재무현황에 아직 '예상' 상태인 항목이 {u}개 있습니다."))
        # 투자현황
        if ym not in inv_months:
            out.append(_finding("missing", "투자현황", ym, "투자현황에 입력된 계좌가 없습니다."))
        elif past and ym not in closed:
            out.append(_finding("missing", "투자현황", ym, "투자현황을 아직 마감하지 않았습니다."))

    if months and not any(_ym(g) == today and g.get("target_amount") for g in tables.get("monthly_goals", [])):
        out.append(_finding("missing", "목표", today, "이번 달 자산 목표가 없습니다."))
    return out


def run_checks(tables: dict, today: tuple) -> list:
    """점검 결과 목록. 최근 달이 먼저 오게 정렬한다."""
    months = data_months(tables, today)
    found = check_investments(tables, months) + check_missing(tables, months, today)
    return sorted(found, key=lambda f: (-f["ym"][0], -f["ym"][1], f["area"]))


# ── AI 에게 넘길 요약 ─────────────────────────────────────
def build_summary(tables: dict, today: tuple, findings: list) -> str:
    """월별 합계 숫자와 점검 결과만 담은 글. 거래 메모·이메일·개별 거래는 넣지 않는다."""
    months = data_months(tables, today)
    inc, fixed, util = (_by_month(tables.get(t, [])) for t in ("monthly_income", "fixed_costs", "utility_costs"))
    closed = closed_months(tables)
    goals = {_ym(g): g.get("target_amount") or 0 for g in tables.get("monthly_goals", [])}
    var, other = {}, {}
    for t in tables.get("transactions", []):
        amt = t.get("amount") or 0
        if t.get("category") == OTHER_INCOME:
            other[_ym(t)] = other.get(_ym(t), 0) + amt
        else:
            c = var.setdefault(_ym(t), {})
            c[t.get("category") or "기타"] = c.get(t.get("category") or "기타", 0) + amt

    def parts(pairs):
        return ", ".join(f"{k} {int(v):,}" for k, v in pairs if v) or "없음"

    lines = [f"오늘: {today[0]}년 {today[1]}월 (이번 달은 아직 진행 중). 금액 단위는 원.", "", "[월별 수입·지출]"]
    for ym in months:
        i, f, u = inc.get(ym, {}), fixed.get(ym, {}), util.get(ym, {})
        inc_p = [(f"{who} {item}", i.get(fld) or 0) for who, item, fld in INCOME_ITEMS] + [("기타 수입", other.get(ym, 0))]
        fix_p = [(grp, sum((f.get(fld) or 0) for _, fld in items)) for grp, items in FIXED_TREE]
        utl_p = [(name, u.get(fld) or 0) for name, fld in UTILITY_ITEMS]
        var_p = sorted(var.get(ym, {}).items(), key=lambda x: -x[1])
        t_inc, t_fix, t_utl, t_var = (sum(v for _, v in p) for p in (inc_p, fix_p, utl_p, var_p))
        lines += [
            f"■ {_label(ym)}: 수입 {t_inc:,} / 지출 {t_fix + t_utl + t_var:,} / 남은 돈 {t_inc - t_fix - t_utl - t_var:,}",
            f"  수입: {parts(inc_p)}",
            f"  고정비 {t_fix:,}: {parts(fix_p)}",
            f"  공과금 {t_utl:,}: {parts(utl_p)}",
            f"  변동지출 {t_var:,}: {parts(var_p)}",
        ]

    lines += ["", "[월별 투자현황: 계좌별 원금/평가액]"]
    series, _ = _inv_series(tables)
    for ym in months:
        rows = [(k, s[ym]) for k, s in sorted(series.items()) if ym in s]
        if not rows:
            lines.append(f"■ {_label(ym)}: 입력 없음")
            continue
        tp, ta = sum(v[0] for _, v in rows), sum(v[1] for _, v in rows)
        state = "마감됨" if ym in closed else "마감 안 함"
        goal = f", 목표 {int(goals[ym]):,}" if goals.get(ym) else ""
        lines.append(f"■ {_label(ym)} ({state}{goal}): 원금 합계 {tp:,} / 평가액 합계 {ta:,}")
        lines += [f"  {k[0]} {k[1]}: 원금 {int(p):,} / 평가액 {int(a):,}" for k, (p, a) in rows]

    lines += ["", "[앱이 규칙으로 찾은 점검 결과]"]
    odd = [f["text"] for f in findings if f["kind"] == "odd"]
    miss = [f["text"] for f in findings if f["kind"] == "missing"]
    lines += ["이상해 보이는 값:"] + ([f"- {t}" for t in odd] or ["- 없음"])
    lines += ["입력 안 된 곳:"] + ([f"- {t}" for t in miss] or ["- 없음"])
    return "\n".join(lines)
