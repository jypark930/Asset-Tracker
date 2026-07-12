import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('.env')
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_ANON_KEY')
client = create_client(url, key)

with open('.session.json', 'r') as f:
    session_data = json.load(f)

# Refresh session
res = client.auth.refresh_session(session_data['refresh_token'])
new_session = res.session
# save new session
with open('.session.json', 'w') as f:
    json.dump({
        "email": new_session.user.email,
        "access_token": new_session.access_token,
        "refresh_token": new_session.refresh_token,
    }, f)

year = 2026
month = 6
owner = '준영'
acc_type = 'TOSS'
principal = 79148591
amount = 76649357

res = client.table('investments').select('*').eq('year', year).eq('month', month).eq('owner', owner).eq('account_type', acc_type).execute()
inv = res.data[0] if res.data else None

if inv:
    print(f"Updating existing TOSS: {inv['id']}")
    client.table('investments').update({
        'principal': principal,
        'amount': amount
    }).eq('id', inv['id']).execute()
    
    # Also replace stocks with a single sum item so dynamic calculation works
    client.table('investment_stocks').delete().eq('investment_id', inv['id']).execute()
    client.table('investment_stocks').insert({
        'investment_id': inv['id'],
        'stock_name': 'TOSS_합산',
        'quantity': 1,
        'average_price': principal,
        'current_price': amount,
        'principal': principal,
        'valuation': amount
    }).execute()
    print("Done")
else:
    print("Not found")
