import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="내 손안의 퀀트", layout="wide")

# --- 데이터 캐싱 (속도 향상) ---
# 주식 리스트를 매번 불러오면 느리니까 한 번만 불러오고 기억하게 합니다.
@st.cache_data
def get_stock_list():
    # 1. 한국 주식 전체 (KRX)
    df_krx = fdr.StockListing('KRX')
    df_krx = df_krx[['Code', 'Name']] # 코드와 이름만 남김
    
    # 2. 미국 주식 (S&P 500)
    df_sp500 = fdr.StockListing('S&P500')
    df_sp500 = df_sp500[['Symbol', 'Name']]
    df_sp500.columns = ['Code', 'Name']
    
    # 3. 인기 미국 주식 한글 맵핑 (사용자 편의)
    # 영어 이름 옆에 한글 별명을 붙여줍니다.
    korean_names = {
        'AAPL': '애플 (Apple)',
        'NVDA': '엔비디아 (NVIDIA)',
        'TSLA': '테슬라 (Tesla)',
        'GOOGL': '구글 (Alphabet)',
        'MSFT': '마이크로소프트 (Microsoft)',
        'AMZN': '아마존 (Amazon)',
        'META': '메타 (Meta)',
        'NFLX': '넷플릭스 (Netflix)'
    }
    
    # S&P500 리스트에 한글 이름 적용
    for code, kor_name in korean_names.items():
        # 해당 코드를 가진 행을 찾아서 이름을 바꿈
        df_sp500.loc[df_sp500['Code'] == code, 'Name'] = kor_name

    # 4. 데이터 합치기
    df_total = pd.concat([df_krx, df_sp500])
    
    # 5. 검색용 라벨 만들기: "삼성전자 (005930)" 형식
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

# --- 사이드바 ---
st.sidebar.title("🔍 분석 옵션")

# 스피너(로딩 표시) 추가
with st.spinner('전 세계 종목 리스트를 불러오는 중...'):
    df_stocks = get_stock_list()

# 검색 기능 (Selectbox)
# 사용자가 선택하면 'Label'을 가져옵니다.
selected_label = st.sidebar.selectbox(
    "종목 검색 (한글/영어/코드)", 
    df_stocks['Label'].values,
    index=0 # 기본값: 리스트 첫 번째
)

# 선택된 라벨에서 '코드'만 추출하기 (괄호 안의 문자열 파싱)
# 예: "삼성전자 (005930)" -> "005930"
ticker = selected_label.split('(')[-1].replace(')', '')

# 경제 지표 선택
indicators = {
    "미국 10년물 국채금리": "FRED:DGS10",
    "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO",
    "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500"
}
selected_name = st.sidebar.selectbox("비교할 경제지표", list(indicators.keys()))
selected_code = indicators[selected_name]

days = st.sidebar.slider("분석 기간(일)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- 데이터 로딩 및 분석 ---
@st.cache_data
def load_data(stock_code, fred_code, start):
    stock = fdr.DataReader(stock_code, start)
    fred = fdr.DataReader(fred_code, start)
    df = pd.concat([stock['Close'], fred], axis=1).dropna()
    df.columns = ['Stock', 'Macro']
    return df

# --- 메인 화면 ---
st.title(f"📈 {selected_label.split('(')[0]} 분석") # 이름만 깔끔하게 출력

try:
    df = load_data(ticker, selected_code, start_date)
    
    # 정규화
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['
