import urllib.request
import json
import streamlit as st

@st.cache_data(ttl=3600)
def get_usd_krw_rate():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read())
        return float(data['rates']['KRW'])
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return 1350.0  # 기본값 Fallback
