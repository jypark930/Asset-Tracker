import sys, os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv('.env')

from utils.db import get_investments, upsert_investment, replace_investment_stocks

invests = get_investments(2026, 6)
toss = [i for i in invests if i['owner'] == '준영' and i['account_type'] == 'TOSS']
if toss:
    inv = toss[0]
    print(f"Current TOSS: principal={inv['principal']}, amount={inv['amount']}")
    # Update to principal = 79,148,591, amount = 76,649,357
    success = upsert_investment(2026, 6, "준영", "TOSS", 79148591, 76649357)
    print(f"Update success: {success}")
    
    # Check if there are stocks
    from utils.db import get_all_investment_stocks
    stocks = get_all_investment_stocks([inv["id"]])
    print(f"Stocks: {len(stocks)}")
    if stocks:
        # If there are stocks, we should probably delete them or replace them with a single stock item
        # so that the dynamic sum equals the new principal and amount!
        print("Replacing stocks with a single sum item to preserve totals...")
        replace_investment_stocks(inv["id"], [
            {
                "stock_name": "TOSS_합산",
                "quantity": 1,
                "average_price": 79148591,
                "current_price": 76649357,
                "principal": 79148591,
                "valuation": 76649357
            }
        ])
        print("Stocks replaced.")
else:
    print("TOSS account not found for Junyeong in June.")
    success = upsert_investment(2026, 6, "준영", "TOSS", 79148591, 76649357)
    print(f"Insert success: {success}")
