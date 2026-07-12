from utils.auth import get_supabase_client
try:
    client = get_supabase_client()
    res = client.table("investments").select("month, principal, amount, account_type").eq("year", 2026).execute()
    print("Investments:", res.data)
except Exception as e:
    print("Error:", e)
