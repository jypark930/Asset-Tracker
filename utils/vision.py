import os
import json
import streamlit as st
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

def analyze_kakao_assets(image_paths):
    """
    여러 장의 이미지를 한 번에 받아 AI가 자체적으로 '평가금액 화면'과 '현재가 화면'을 짝지어 분석하고,
    계좌별로 분류된 종목 데이터를 JSON 형태로 추출합니다.
    """
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    images = [Image.open(p) for p in image_paths]

    prompt = """
당신은 금융 데이터 추출 전문가입니다. 사용자가 올린 여러 장의 카카오톡 자산 모아보기 캡처 화면들을 분석해야 합니다.
이미지들 속에는 여러 계좌(예: KB, 업비트, TOSS, 중개형ISA, 청년도약 등)의 화면들이 섞여 있습니다.

[작업 지시사항]
1. 이미지 내의 글자를 읽고, 어떤 증권사/은행/계좌명인지 파악하여 아래 '지원하는 계좌명' 중 하나로 매핑하세요.
   - 지원하는 계좌명: 주택청약, IRP, 중개형ISA, 청년도약, CMA, KB, TOSS, 업비트, 총 예수금
   - **중요**: 계좌명이 "총 예수금"으로 인식된 경우, 종목명을 반드시 `"예수금(현금)"`과 `"예수금(달러)"`로 구분하세요.
     * 달러 자산: 종목명을 `"예수금(달러)"`로 설정하고, `quantity`에 **보유한 달러($) 금액 전체**를 입력하세요. (평가금액/원금도 달러 수량과 동일하게 입력).
     * 현금(원화) 자산: 종목명을 `"예수금(현금)"`으로 설정하고 `quantity`는 1로, 원금과 평가액은 해당 원화 금액으로 설정하세요.
2. 동일한 계좌의 '평가금액 조회 화면'과 '현재가 조회 화면' 이미지를 스스로 짝지어 종목별 데이터를 계산하세요.
   - 보유수량 = 평가금액 / 현재가 (소수점 첫째 자리까지 유지, 예: 3.1)
   - 원금 = 평가금액 - 손익금액
   (단, 예적금이나 특정 화면에서는 현재가/수량이 없을 수 있습니다. 이 경우 원금과 평가금액만 추출하세요.)
3. 결과를 다음과 같은 계좌 단위로 그룹화된 순수 JSON 배열(Array)로만 출력하세요. 마크다운(```json)이나 텍스트는 절대 포함하지 마세요.

[
  {
    "account_name": "KB",
    "stocks": [
      {
        "stock_name": "삼성전자",
        "quantity": 10.0,
        "average_price": 75000,
        "current_price": 80000,
        "principal": 750000,
        "valuation": 800000
      }
    ]
  },
  {
    "account_name": "업비트",
    "stocks": [
      {
        "stock_name": "비트코인",
        "quantity": 0.5,
        "average_price": 80000000,
        "current_price": 90000000,
        "principal": 40000000,
        "valuation": 45000000
      }
    ]
  }
]
"""
    try:
        contents = [prompt] + images
        response = model.generate_content(contents)
        text = response.text.strip()
        # Remove markdown code blocks if the model still adds them
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as je:
            st.error(f"JSON 파싱 실패! AI 응답 원본:\n\n{text}")
            return None
    except Exception as e:
        st.error(f"AI 통신 에러 발생: {e}")
        return None
