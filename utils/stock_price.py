"""
utils/stock_price.py
네이버 금융 API를 통한 주식 현재가 조회
"""
import re
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Referer": "https://finance.naver.com/",
    "Accept": "application/json",
}

def search_stock_code(name: str) -> tuple[str, str] | None:
    """종목명 → (코드, 종목명) 검색"""
    try:
        resp = httpx.get(
            "https://ac.finance.naver.com/ac",
            params={"q": name, "q_enc": "UTF-8", "target": "stock,etf,index"},
            headers=HEADERS, timeout=5,
        )
        data = resp.json()
        items = data.get("items", [])
        if items and items[0]:
            row = items[0][0]  # 첫 번째 결과
            # row = [종목명, 코드, 거래소, ...]
            return str(row[1]), str(row[0])  # (code, display_name)
    except Exception as e:
        print(f"[stock_price] search error for '{name}': {e}")
    return None


def get_current_price(name_or_code: str) -> dict | None:
    """
    종목명 또는 6자리 코드로 현재가 조회
    Returns: {"code": str, "name": str, "price": int} 또는 None
    """
    query = name_or_code.strip()

    # 6자리 숫자 → 종목코드 직접 사용
    if re.match(r"^\d{6}$", query):
        code, display_name = query, query
    else:
        result = search_stock_code(query)
        if not result:
            print(f"[stock_price] code not found for '{query}'")
            return None
        code, display_name = result

    # 네이버 모바일 API로 현재가 조회
    try:
        resp = httpx.get(
            f"https://m.stock.naver.com/api/stock/{code}/basic",
            headers=HEADERS, timeout=5,
        )
        if resp.status_code == 200:
            info = resp.json().get("stockInfo", {})
            price_str = str(info.get("closePrice", "0")).replace(",", "")
            name = info.get("stockName", display_name)
            price = int(price_str) if price_str.isdigit() else 0
            if price > 0:
                return {"code": code, "name": name, "price": price}
    except Exception as e:
        print(f"[stock_price] price fetch error for '{code}': {e}")

    return None


def get_prices_bulk(name_or_code_list: list[str]) -> dict[str, dict]:
    """
    여러 종목 일괄 조회
    Returns: {입력값: {"code", "name", "price"}}
    """
    result = {}
    for item in name_or_code_list:
        if item.strip():
            result[item] = get_current_price(item)
    return result
