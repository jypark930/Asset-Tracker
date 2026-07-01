import streamlit as st
import csv
import io
from utils.auth import get_current_user, get_supabase_client

st.set_page_config(page_title="6월 업데이트", page_icon="📝", layout="wide")

st.title("📝 6월 투자현황 업데이트 (임시)")

csv_text = """계좌,종목명,평가액,원금,손익,평단가,수량,현재가
지윤ISA,현대차2우B,10775000,8185500,2589500,163710,50,215500
지윤ISA,LG화학우,6165000,5836500,328500,129700,45,137000
지윤ISA,NH투자증권우,3592500,2584500,1008000,17230,150,23950
지윤ISA,서울보증보험,3320000,3388000,-68000,42350,80,41500
지윤ISA,TIGER코스닥150,1432250,1687250,-255000,19850,85,16850
지윤ISA,기업은행,218900,246400,-27500,22400,11,19900
지윤TOSS,삼성화재우,8140000,7205000,935000,360250,20,407000
지윤TOSS,현대차우,3472000,3222750,249250,201421,16,217000
지윤TOSS,NH투자증권우,2395000,2385000,10000,23850,100,23950
지윤TOSS,기업은행,661650,663300,-1650,20100,33,20050
지윤TOSS,BITO,2361066,4372784,-2011718,22839,191.46,12328
지윤TOSS,GLD,1138920,1181783,-42863,590892,2,569459
지윤TOSS,CONY,878654,1153803,-275149,38460,30,29286
지윤TOSS,스페이스X,509865,607667,-97802,303833,2,254919
지윤TOSS,VOO,33206,32967,239,1047003,0.03,1054578
지윤CMA,,12211243,12211243,,,,
지윤 청년도약계좌,,16100000,16100000,,,,
지윤 청년주택드림,,5726900,5726900,,,,
지윤 IRP,,3694272,3694272,,,,
업비트,솔라나,1945049,3196191,-1251142,184536,17.32011645,112300
업비트,도지코인,202801,400840,-198038,215.4,1860.56148163,109
업비트,예수금,300000,300000,,,,
준영 청년도약계좌,,17500000,17500000,,,,
준영 주택청약,,9800000,9800000,,,,
준영 CMA,,10011562,10011562,,,,
준영 연금저축,,1414674,1414674,,,,
준영TOSS,NH투자증권우,14920850,11472240,3448610,18414,623,23950
준영TOSS,대신증권우,10375200,10838600,-463400,20527,528,19650
준영TOSS,LG화학우,8220000,7325000,895000,122083,60,137000
준영TOSS,삼성화재우,8140000,7450000,690000,372500,20,407000
준영TOSS,현대차우,7812000,7977600,-165600,221600,36,217000
준영TOSS,한국투자 ACE 고배당주증권 ETF,5160000,4374000,786000,10935,400,12900
준영TOSS,삼성전자,4995000,5452500,-457500,363500,15,333000
준영TOSS,삼성증권,3288000,3012000,276000,100400,30,109600
준영TOSS,두산로보틱스,724800,880000,-155200,110000,8,90600
준영TOSS,LG에너지솔루션,362500,394500,-32000,394500,1,362500
준영TOSS,KODEX 미국S&P500,261150,254200,6950,25420,10,26115
준영TOSS,비덴트,185920,520170,-334250,9288,56,3320
준영TOSS,BITO,3647064,5940534,-2293470,19961,297.695,12251
준영TOSS,CONY,2927308,3762457,-835149,37624,100,29270
준영TOSS,테이크-투 인터랙티브...,1133649,1140032,-6383,380010,3,377880
준영TOSS,코인베이스 글로벌,1126064,1420159,-294095,284032,5,225200
준영TOSS,VOO,1051210,1044859,6351,1044858,1,1051199
준영TOSS,ETHU,1004130,4450935,-3446805,76666,58.366,17204
준영TOSS,레드와이어,722624,810598,-87974,20784,39.027,18516
준영TOSS,GLD,569229,585664,-16435,585664,1,569228
준영TOSS,Invesco QQQ Trust Series 1,22657,22517,140,1112554,0.0202,1119461
준영TOSS,예수금,279398,279398,,,,
준영ISA,대신증권우,19060500,15449300,3611200,15927,970,19650
준영ISA,삼성화재우,9361000,6382500,2978500,277500,23,407000
준영ISA,기업은행,6527200,4986940,1540260,15204,328,19900
준영ISA,NH투자증권우,4790000,3060000,1730000,15300,200,23950
준영ISA,TIGER코스닥150,4718000,5558000,-840000,19850,280,16850
준영ISA,현대차2우B,4525500,3066000,1459500,146000,21,215500
준영ISA,코리안리,4488640,3778840,709800,11180,338,13280
준영ISA,서울보증보험,4150000,3385000,765000,33850,100,41500
준영ISA,KODEX 미국배당커버드...,3060000,2957550,102450,13144,225,13600
준영ISA,우리금융지주,2900000,1668000,1232000,16680,100,29000
준영ISA,CJ우,403200,425400,-22200,70900,6,67200
준영ISA,예수금,116150,116150,,,,
준영KB,SK,12510000,4380190,8129810,292012,15,834000
준영KB,NAVER,5970000,7800340,-1830340,260011,30,199000
준영KB,예수금,149538,149538,,,,
"""

def parse_val(s):
    if not s.strip(): return 0
    try:
        return float(s.strip())
    except:
        return 0

def get_owner_and_type(raw_acc):
    if raw_acc.startswith("지윤"):
        owner = "지윤"
        raw_acc = raw_acc.replace("지윤", "").strip()
    elif raw_acc.startswith("준영"):
        owner = "준영"
        raw_acc = raw_acc.replace("준영", "").strip()
    elif raw_acc == "업비트":
        owner = "준영"
    else:
        owner = "준영"
        
    acc_map = {
        "ISA": "중개형ISA",
        "TOSS": "TOSS",
        "CMA": "CMA",
        "청년도약계좌": "청년도약",
        "청년주택드림": "주택청약",
        "주택청약": "주택청약",
        "IRP": "IRP",
        "연금저축": "IRP",
        "업비트": "업비트",
        "KB": "KB",
    }
    
    acc_type = acc_map.get(raw_acc, raw_acc)
    return owner, acc_type

if st.button("🚀 6월 데이터 데이터베이스에 업로드하기"):
    user = get_current_user()
    if not user:
        st.error("로그인이 필요합니다.")
        st.stop()
        
    user_id = user.id
    client = get_supabase_client()
    
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    accounts = {}
    
    for row in reader:
        raw_acc = row["계좌"].strip()
        owner, acc_type = get_owner_and_type(raw_acc)
        
        key = (owner, acc_type)
        if key not in accounts:
            accounts[key] = {"stocks": [], "total_p": 0, "total_a": 0}
            
        name = row["종목명"].strip()
        p = parse_val(row["원금"])
        a = parse_val(row["평가액"])
        qty = parse_val(row["수량"])
        avg_price = parse_val(row["평단가"])
        cur_price = parse_val(row["현재가"])
        
        accounts[key]["total_p"] += p
        accounts[key]["total_a"] += a
        
        if name:
            accounts[key]["stocks"].append({
                "stock_name": name,
                "quantity": qty,
                "average_price": avg_price,
                "current_price": cur_price,
                "principal": int(p),
                "valuation": int(a)
            })

    year = 2026
    month = 6
    
    progress = st.progress(0)
    total = len(accounts)
    
    for i, ((owner, acc_type), data) in enumerate(accounts.items()):
        # 1. Upsert investment
        res = client.table("investments").upsert({
            "user_id": user_id, "year": year, "month": month,
            "owner": owner, "account_type": acc_type,
            "principal": int(data["total_p"]), "amount": int(data["total_a"]),
        }, on_conflict="user_id,year,month,owner,account_type").execute()
        
        # 2. Get the investment ID
        res2 = client.table("investments").select("id").eq("user_id", user_id).eq("year", year).eq("month", month).eq("owner", owner).eq("account_type", acc_type).execute()
        if res2.data:
            inv_id = res2.data[0]["id"]
            
            # 3. Update stocks
            client.table("investment_stocks").delete().eq("investment_id", inv_id).execute()
            if data["stocks"]:
                insert_data = []
                for s in data["stocks"]:
                    s["investment_id"] = inv_id
                    insert_data.append(s)
                client.table("investment_stocks").insert(insert_data).execute()
                
        progress.progress((i + 1) / total)
        
    st.success("✅ 6월 투자현황 업로드가 성공적으로 완료되었습니다! 이제 왼쪽 사이드바에서 [4_📈_투자현황] 페이지로 이동해 확인해보세요.")
