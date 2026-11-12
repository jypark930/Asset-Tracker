"""
utils/fin.py
재무현황(수입·고정비·공과금) 항목 정의와 '확정/예상' 계산. 재무현황·대시보드가 함께 쓴다.
"""

INCOME_ITEMS = [  # (사람, 항목, 필드)
    ("준영", "정기급여", "junyoung_salary"),
    ("준영", "상여금", "junyoung_bonus"),
    ("지윤", "정기급여", "jiyun_salary"),
    ("지윤", "인센티브", "jiyun_incentive"),
]

FIXED_TREE = [  # (분류, [(항목, 필드)])
    ("주거비", [("주담대 원리금", "loan_payment"), ("관리비", "maintenance_fee"), ("월세", "rent")]),
    ("보험", [("자동차 보험", "car_insurance"), ("운전자 보험", "driver_insurance"),
             ("실비/건강보험", "health_insurance"), ("암보험", "cancer_insurance"),
             ("태아/어린이 보험", "fetal_insurance"), ("애기 실손보험", "baby_health_insurance")]),
    ("차량유지비", [("자동차세", "car_tax"), ("세차비", "car_wash")]),
    ("통신비", [("준영 휴대폰", "junyoung_phone"), ("지윤 휴대폰", "jiyun_phone"), ("인터넷/TV", "internet")]),
    ("교통비", [("준영 교통비", "junyoung_transport"), ("지윤 교통비", "jiyun_transport"),
               ("차량 주유비", "fuel"), ("하이패스", "hipass")]),
    ("기타 지출", [("준영 모임통장", "junyoung_club"), ("지윤 모임통장", "jiyun_club"),
                ("준영 부모님 용돈", "junyoung_parents"), ("지윤 부모님 용돈", "jiyun_parents")]),
    ("구독·멤버십", [("쿠팡 와우", "coupang"), ("유튜브", "youtube"), ("네이버멤버십", "naver"),
                 ("AI서비스", "antigravity")]),
    ("저축", [("준영 희망적금", "junyoung_savings1"), ("준영 주택청약", "junyoung_savings2"),
            ("지윤 희망적금", "jiyun_savings1"), ("지윤 주택청약", "jiyun_savings2")]),
    ("개인 용돈", [("준영 용돈", "junyoung_allowance"), ("지윤 용돈", "jiyun_allowance")]),
]

UTILITY_ITEMS = [("전기세", "electricity"), ("수도세", "water"), ("가스비", "gas"), ("주민세", "resident_tax")]

# 가계부 카테고리 → 재무현황 묶음 (자동 연동, 읽기 전용)
VARIABLE_GROUPS = [
    ("생활지출", ["식비", "생필품비", "간식비", "외식비", "문화비", "준영점심"]),
    ("아가", ["아가 식비", "아가 생필품비", "아가 용품/의류비", "아가 병원/의료비", "아가 활동/교육비"]),
    ("의료비", ["의료비"]),
    ("경조/선물비", ["경조비"]),
]

INCOME_FIELDS = [f for _, _, f in INCOME_ITEMS]
FIXED_FIELDS = [f for _, items in FIXED_TREE for _, f in items]
UTILITY_FIELDS = [f for _, f in UTILITY_ITEMS]

_SKIP = {"id", "year", "month", "user_id", "updated_by", "updated_at", "created_at", "confirmed_fields"}


def confirmed_fields(raw: dict) -> list:
    """확정된 필드 목록. 예전 '시스템' 자동 입력 행은 숫자 필드를 모두 확정으로 본다."""
    if not raw:
        return []
    cf = raw.get("confirmed_fields")
    if isinstance(cf, list) and cf:
        return list(cf)
    if raw.get("updated_by") == "시스템":
        return [k for k, v in raw.items() if isinstance(v, (int, float)) and k not in ("id", "year", "month", "user_id")]
    return []


def merge_month(curr_raw: dict, prev_raw: dict) -> tuple[dict, list]:
    """이번 달 값 우선, 비어 있으면 전월 값을 예상치로 (B3)."""
    curr = curr_raw or {}
    prev = prev_raw or {}
    cf = confirmed_fields(curr)
    res = {}
    for k in set(curr) | set(prev):
        if k in _SKIP:
            continue
        if k in cf or (curr and curr.get(k) is not None):
            res[k] = curr.get(k, 0)
        else:
            res[k] = prev.get(k, 0)
    return res, cf


def unconfirmed_count(inc_raw: dict, fixed_raw: dict, util_raw: dict) -> int:
    n = 0
    for raw, fields in ((inc_raw, INCOME_FIELDS), (fixed_raw, FIXED_FIELDS), (util_raw, UTILITY_FIELDS)):
        cf = set(confirmed_fields(raw))
        n += sum(1 for f in fields if f not in cf)
    return n
