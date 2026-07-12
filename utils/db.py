"""
utils/db.py
Supabase DB CRUD 유틸리티 - 엑셀 구조 기반
"""
import streamlit as st
from datetime import datetime, timezone
from utils.auth import get_supabase_client, get_current_user, get_current_user_email

CATEGORIES = ["외식비", "식비", "생필품비", "간식비", "준영점심", "의료비", "문화비", "경조비"]

FIXED_COST_LABELS = {
    "loan_payment":       "대출 상환액",
    "rent":               "빌라 월세",
    "maintenance_fee":    "빌라 관리비",
    "car_tax":            "차량세",
    "car_insurance":      "차량 보험",
    "driver_insurance":   "운전자 보험",
    "health_insurance":   "실손 보험",
    "cancer_insurance":   "암 보험",
    "junyoung_phone":     "준영 통신비",
    "jiyun_phone":        "지윤 통신비",
    "internet":           "인터넷 비용",
    "junyoung_transport": "준영 교통비",
    "jiyun_transport":    "지윤 교통비",
    "fuel":               "차량 유류비",
    "hipass":             "하이패스",
    "junyoung_club":      "준영 모임통장",
    "jiyun_club":         "지윤 모임통장",
    "junyoung_parents":   "준영 부모님 용돈",
    "jiyun_parents":      "지윤 부모님 용돈",
    "coupang":            "쿠팡 와우",
    "youtube":            "유튜브",
    "naver":              "네이버 멤버십",
    "antigravity":        "안티그래비티",
    "junyoung_savings1":  "준영 청년희망적금",
    "junyoung_savings2":  "준영 주택청약적금",
    "jiyun_savings1":     "지윤 청년희망적금",
    "jiyun_savings2":     "지윤 주택청약적금",
    "junyoung_allowance": "준영 용돈",
    "jiyun_allowance":    "지윤 용돈",
}

FIXED_COST_GROUPS = {
    "🏠 주거비":    ["loan_payment", "rent", "maintenance_fee"],
    "🚗 차량/보험": ["car_tax", "car_insurance", "driver_insurance", "health_insurance", "cancer_insurance"],
    "📱 통신비":    ["junyoung_phone", "jiyun_phone", "internet"],
    "🚌 교통비":    ["junyoung_transport", "jiyun_transport", "fuel", "hipass"],
    "💬 기타":      ["junyoung_club", "jiyun_club", "junyoung_parents", "jiyun_parents"],
    "📺 구독":      ["coupang", "youtube", "naver", "antigravity"],
    "🏦 예적금":    ["junyoung_savings1", "junyoung_savings2", "jiyun_savings1", "jiyun_savings2"],
    "💸 용돈":      ["junyoung_allowance", "jiyun_allowance"],
}
INVESTMENT_ACCOUNTS = {
    "비현금성 자산": ["주택청약", "IRP", "중개형ISA"],
    "현금성 자산": ["TOSS", "KB", "총 예수금", "CMA", "업비트", "청년도약"]
}

def _uid():
    user = get_current_user()
    if not user:
        st.error("로그인이 필요합니다.")
        st.stop()
    return user.id


# ─── Transactions (변동지출) ───────────────────────────────

def get_transactions(year: int, month: int) -> list:
    client = get_supabase_client()
    res = (client.table("transactions").select("*")
           .eq("year", year).eq("month", month)
           .neq("category", "기타 수입")
           .order("day").execute())
    return res.data or []

def get_other_incomes(year: int, month: int) -> list:
    client = get_supabase_client()
    res = (client.table("transactions").select("*")
           .eq("year", year).eq("month", month)
           .eq("category", "기타 수입")
           .order("created_at").execute())
    return res.data or []


def insert_transaction(year: int, month: int, day: int, amount: int,
                       description: str, category: str) -> bool:
    try:
        get_supabase_client().table("transactions").insert({
            "user_id": _uid(), "year": year, "month": month, "day": day,
            "amount": amount, "description": description, "category": category,
        }).execute()
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False


def update_transaction(tx_id: str, data: dict) -> bool:
    try:
        get_supabase_client().table("transactions").update(data).eq("id", tx_id).execute()
        return True
    except Exception as e:
        st.error(f"수정 실패: {e}")
        return False


def delete_transaction(tx_id: str) -> bool:
    try:
        get_supabase_client().table("transactions").delete().eq("id", tx_id).execute()
        return True
    except Exception as e:
        st.error(f"삭제 실패: {e}")
        return False


# ─── Monthly Income (월별 수입) ───────────────────────────

def get_monthly_income(year: int, month: int) -> dict:
    client = get_supabase_client()
    res = (client.table("monthly_income").select("*")
           .eq("year", year).eq("month", month).execute())
    return res.data[0] if res.data else {}


def upsert_monthly_income(year: int, month: int, data: dict, confirmed_fields: list = None) -> bool:
    try:
        existing = get_monthly_income(year, month)
        owner_id = existing.get("user_id", _uid()) if existing else _uid()
        data.update({
            "user_id":    owner_id,
            "year":       year,
            "month":      month,
            "updated_by": get_current_user_email(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        if confirmed_fields is not None:
            data["confirmed_fields"] = confirmed_fields
        get_supabase_client().table("monthly_income").upsert(
            data, on_conflict="user_id,year,month").execute()
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False


# ─── Fixed Costs (고정비) ─────────────────────────────────

def get_fixed_costs(year: int, month: int) -> dict:
    client = get_supabase_client()
    res = (client.table("fixed_costs").select("*")
           .eq("year", year).eq("month", month).execute())
    return res.data[0] if res.data else {}


def upsert_fixed_costs(year: int, month: int, data: dict, confirmed_fields: list = None) -> bool:
    try:
        existing = get_monthly_income(year, month)
        owner_id = existing.get("user_id", _uid()) if existing else _uid()
        data.update({
            "user_id":    owner_id,
            "year":       year,
            "month":      month,
            "updated_by": get_current_user_email(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        if confirmed_fields is not None:
            data["confirmed_fields"] = confirmed_fields
        get_supabase_client().table("fixed_costs").upsert(
            data, on_conflict="user_id,year,month").execute()
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False


# ─── Utility Costs (공과금) ───────────────────────────────

def get_utility_costs(year: int, month: int) -> dict:
    client = get_supabase_client()
    res = (client.table("utility_costs").select("*")
           .eq("year", year).eq("month", month).execute())
    return res.data[0] if res.data else {}


def upsert_utility_costs(year: int, month: int, data: dict, confirmed_fields: list = None) -> bool:
    try:
        existing = get_utility_costs(year, month)
        owner_id = existing.get("user_id", _uid()) if existing else _uid()
        data.update({
            "user_id":    owner_id,
            "year":       year,
            "month":      month,
            "updated_by": get_current_user_email(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        if confirmed_fields is not None:
            data["confirmed_fields"] = confirmed_fields
        get_supabase_client().table("utility_costs").upsert(
            data, on_conflict="user_id,year,month").execute()
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False


# ─── Investments (투자 자산) ──────────────────────────────

def get_investments(year: int, month: int) -> list:
    client = get_supabase_client()
    res = (client.table("investments").select("*")
           .eq("year", year).eq("month", month)
           .order("owner").execute())
    return res.data or []


def upsert_investment(year: int, month: int, owner: str, account_type: str, principal: int, amount: int) -> bool:
    try:
        get_supabase_client().table("investments").upsert({
            "user_id": _uid(), "year": year, "month": month,
            "owner": owner, "account_type": account_type,
            "principal": principal, "amount": amount,
        }, on_conflict="user_id,year,month,owner,account_type").execute()

        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False


# ─── Dashboard Summary ────────────────────────────────────

def get_monthly_summary(year: int, month: int) -> dict:
    income   = get_monthly_income(year, month)
    txns     = get_transactions(year, month)
    fixed    = get_fixed_costs(year, month)
    utility  = get_utility_costs(year, month)
    invests  = get_investments(year, month)
    other_incomes = get_other_incomes(year, month)

    total_income = (income.get("junyoung_salary", 0) + income.get("junyoung_bonus", 0) +
                    income.get("jiyun_salary", 0)    + income.get("jiyun_incentive", 0) +
                    sum(item.get("amount", 0) for item in other_incomes))

    total_variable = sum(t.get("amount", 0) for t in txns)

    category_totals = {}
    for t in txns:
        cat = t.get("category", "기타")
        category_totals[cat] = category_totals.get(cat, 0) + t.get("amount", 0)

    total_fixed = sum(fixed.get(f, 0) for f in FIXED_COST_LABELS)
    total_utility = utility.get("electricity", 0) + utility.get("water", 0) + utility.get("gas", 0)
    total_expense = total_fixed + total_utility + total_variable
    total_investment = sum(inv.get("amount", 0) for inv in invests)
    total_principal = sum(inv.get("principal", 0) for inv in invests)

    return {
        "total_income":    total_income,
        "total_variable":  total_variable,
        "total_fixed":     total_fixed,
        "total_utility":   total_utility,
        "total_expense":   total_expense,
        "net":             total_income - total_expense,
        "category_totals": category_totals,
        "total_investment": total_investment,
        "total_principal": total_principal,
        "investments":     invests,
        "income_detail":   income,
        "fixed_detail":    fixed,
        "utility_detail":  utility,
    }

# ─── Investment Stocks (주식 종목) ────────────────────────
def get_investment_stocks(investment_id: str) -> list:
    try:
        res = get_supabase_client().table("investment_stocks").select("*").eq("investment_id", investment_id).order("valuation", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"Error fetching stocks: {e}")
        return []

def get_all_investment_stocks(investment_ids: list) -> list:
    if not investment_ids:
        return []
    try:
        res = get_supabase_client().table("investment_stocks").select("*").in_("investment_id", investment_ids).order("valuation", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"Error fetching all stocks: {e}")
        return []

def replace_investment_stocks(investment_id: str, stocks: list) -> bool:
    client = get_supabase_client()
    try:
        # 먼저 기존 종목 모두 삭제
        client.table("investment_stocks").delete().eq("investment_id", investment_id).execute()
        # 새로운 종목들 삽입
        if stocks:
            for s in stocks:
                s["investment_id"] = investment_id
            client.table("investment_stocks").insert(stocks).execute()
        return True
    except Exception as e:
        st.error(f"종목 저장 실패: {e}")
        return False

def copy_previous_month_investments(year: int, month: int) -> bool:
    client = get_supabase_client()
    try:
        curr_invs = get_investments(year, month)
        curr_keys = set((i["owner"], i["account_type"]) for i in curr_invs)
            
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        prev_invs = get_investments(prev_year, prev_month)
        if not prev_invs:
            return False
            
        user_id = _uid()
        copied_any = False
        
        for p_inv in prev_invs:
            key = (p_inv["owner"], p_inv["account_type"])
            if key not in curr_keys:
                res = client.table("investments").insert({
                    "user_id": user_id, "year": year, "month": month,
                    "owner": p_inv["owner"], "account_type": p_inv["account_type"],
                    "principal": p_inv.get("principal", 0), "amount": p_inv.get("amount", 0)
                }).execute()
                
                if res.data:
                    copied_any = True
                    new_inv_id = res.data[0]["id"]
                    p_inv_id = p_inv["id"]
                    p_stocks = get_investment_stocks(p_inv_id)
                    
                    if p_stocks:
                        new_stocks = []
                        for s in p_stocks:
                            new_s = {k: v for k, v in s.items() if k not in ("id", "investment_id", "created_at")}
                            new_s["investment_id"] = new_inv_id
                            new_stocks.append(new_s)
                        client.table("investment_stocks").insert(new_stocks).execute()
                        
        return copied_any
    except Exception as e:
        print(f"Error copying previous month investments: {e}")
        return False

# ─── Monthly Goals (월별 자산 목표) ──────────────────────
def get_monthly_goals(year: int) -> list:
    try:
        res = get_supabase_client().table("monthly_goals").select("*").eq("year", year).order("month").execute()
        return res.data or []
    except Exception as e:
        print(f"Error fetching monthly goals: {e}")
        return []

def get_monthly_goal(year: int, month: int) -> dict:
    try:
        res = get_supabase_client().table("monthly_goals").select("*").eq("year", year).eq("month", month).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"Error fetching monthly goal: {e}")
        return {}

def upsert_monthly_goal(year: int, month: int, target_amount: int, cash_target_amount: int = 0) -> bool:
    try:
        get_supabase_client().table("monthly_goals").upsert({
            "user_id": _uid(), "year": year, "month": month, 
            "target_amount": target_amount, "cash_target_amount": cash_target_amount
        }, on_conflict="user_id,year,month").execute()
        return True
    except Exception as e:
        st.error(f"목표 저장 실패: {e}")
        return False
def get_yearly_cash_assets(year: int) -> dict:
    try:
        client = get_supabase_client()
        # 1. 월별 목표 데이터 조회
        goals_res = client.table("monthly_goals").select("*").eq("year", year).execute()
        goals = {g["month"]: g.get("cash_target_amount", 0) for g in (goals_res.data or [])}
        
        # 2. 현금성 자산 데이터 조회
        cash_accounts = INVESTMENT_ACCOUNTS.get("현금성 자산", [])
        inv_res = client.table("investments").select("month, principal, amount, account_type").eq("year", year).execute()
        
        yearly_data = {}
        for m in range(1, 13):
            yearly_data[m] = {"target": goals.get(m, 0), "principal": 0, "evaluation": 0}
            
        if inv_res.data:
            for inv in inv_res.data:
                if inv.get("account_type") in cash_accounts:
                    m = inv.get("month")
                    if m in yearly_data:
                        yearly_data[m]["principal"] += inv.get("principal", 0)
                        yearly_data[m]["evaluation"] += inv.get("amount", 0)
                        
        return yearly_data
    except Exception as e:
        print(f"Error fetching yearly cash assets: {e}")
        return {m: {"target": 0, "principal": 0, "evaluation": 0} for m in range(1, 13)}
