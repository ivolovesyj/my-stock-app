import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="내 손안의 퀀트", layout="wide")

# --- 데이터 캐싱 (속도 향상 및 안정성) ---
@st.cache_data
def get_stock_list():
    # 1. 한국 주식 전체 (KRX)
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx[['Code', 'Name']]
    except:
        # 만약 에러나면 기본값 사용
        df_krx = pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']})

    # 2. 미국 주식 및 검색 편의를 위한 매핑
    # (미국 전체 리스트는 너무 무거워서 인기 종목 위주로 구성했습니다)
    us_stocks = {
        'AAPL': '애플 (Apple)',
        'NVDA': '엔비디아 (NVIDIA)',
        'TSLA': '테슬라 (Tesla)',
        'MSFT': '마이크로소프트 (Microsoft)',
        'GOOGL': '구글 (Google/Alphabet)',
        'AMZN': '아마존 (Amazon)',
        'META': '메타 (Meta/Facebook)',
        'NFLX': '넷플릭스 (Netflix)',
        'AMD': 'AMD',
        'INTC': '인텔 (Intel)',
        'QQQ': '나스닥 추종 ETF (QQQ)',
        'SPY': 'S&P500 추종 ETF (SPY)',
        'SOXL': '반도체 3배 레버리지 (SOXL)',
        'TQQQ': '나스닥 3배 레버리지 (TQQQ)'
    }
    
    # 데이터프레임으로 변환
    df_us = pd.DataFrame(list(us_stocks.items()), columns=['Code', 'Name'])
    
    # 3. 한국 + 미국 합치기
    df_total = pd.concat([df_krx, df_us])
    
    # 4. 검색용 라벨 만들기: "이름 (코드)"
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

# --- 사이드바 ---
st.sidebar.title("🔍 분석 옵션")

# 종목 리스트 불러오기
try:
    with st.spinner('종목 리스트를 불러오는 중...'):
        df_stocks = get_stock_list()
    
    # 검색 기능
    # 기본값은 삼성전자가 되도록 설정
    default_index = 0
    if not df_stocks.empty:
        # 삼성전자를 찾아서 기본값으로 설정 (없으면 0번)
        matches = df_stocks.index[df_stocks['Code'] == '005930'].tolist()
        if matches:
            default_index = matches[0]

    selected_label = st.sidebar.selectbox(
        "종목 검색 (한글/영어 이름)", 
        df_stocks['Label'].values,
        index=default_index if default_index < len(df_stocks) else 0
    )
    
    # 코드 추출: "삼성전자 (005930)" -> "005930"
    ticker = selected_label.split('(')[-1].replace(')', '')

except Exception as e:
    st.sidebar.error("종목 리스트 로딩 실패. 코드를 직접 입력하세요.")
    ticker = st.sidebar.text_input("종목 코드", "005930")


# 경제 지표 선택
indicators = {
    "미국 10년물 국채금리": "FRED:DGS10",
    "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO",
    "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500",
    "미국 기준금리": "FRED:FEDFUNDS"
}
selected_name = st.sidebar.selectbox("비교할 경제지표", list(indicators.keys()))
selected_code = indicators[selected_name]

days = st.sidebar.slider("분석 기간(일)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- 데이터 로딩 및 분석 함수 ---
@st.cache_data
def load_data(stock_code, fred_code, start):
    try:
        stock = fdr.DataReader(stock_code, start)
        fred = fdr.DataReader(fred_code, start)
        
        # 데이터가 없으면 에러 발생시키기
        if stock.empty or fred.empty:
            return None

        # 데이터 합치기 (날짜 기준 교집합)
        df = pd.concat([stock['Close'], fred], axis=1).dropna()
        df.columns = ['Stock', 'Macro']
        return df
    except:
        return None

# --- 메인 화면 ---
st.title(f"📈 {ticker} vs {selected_name}")

# 데이터 가져오기
df = load_data(ticker, selected_code, start_date)

if df is not None and not df.empty:
    # 정규화 (0~1) - 여기가 아까 에러났던 부분!
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
    
    # 괴리율 계산
    gap = df['Stock_Norm'].iloc[-1] - df['Macro_Norm'].iloc[-1]
    
    # 1. 숫자 지표
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 주가", f"{df['Stock'].iloc[-1]:,.0f}")
    col2.metric(f"지표 ({selected_name})", f"{df['Macro'].iloc[-1]:.2f}")
    
    state = "⚠️ 과열/괴리 발생" if abs(gap) > 0.5 else "✅ 안정/동조화"
    col3.metric("괴리율 상태", state, f"{gap:.2f}")

    # 2. 차트 그리기
    st.subheader("추세 비교 차트")
    fig = go.Figure()
    # 주가 (파란 실선)
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue', width=2)))
    # 경제지표 (빨간 점선)
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name=selected_name + ' (정규화)', line=dict(color='red', dash='dot')))
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 Tip: 그래프 오른쪽 위의 도구들을 이용해 확대/축소할 수 있습니다.")

else:
    st.error("데이터를 불러올 수 없습니다. (종목 코드나 날짜를 확인해주세요)")
