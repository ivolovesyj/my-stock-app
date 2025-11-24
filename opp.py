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
        df_krx = pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']})

    # 2. 미국 주식 (주요 종목)
    us_stocks = {
        'AAPL': '애플 (Apple)',
        'NVDA': '엔비디아 (NVIDIA)',
        'TSLA': '테슬라 (Tesla)',
        'MSFT': '마이크로소프트 (Microsoft)',
        'GOOGL': '구글 (Alphabet)',
        'AMZN': '아마존 (Amazon)',
        'META': '메타 (Meta)',
        'NFLX': '넷플릭스 (Netflix)',
        'AMD': 'AMD',
        'INTC': '인텔 (Intel)',
        'QQQ': '나스닥 ETF (QQQ)',
        'SPY': 'S&P500 ETF (SPY)',
        'SOXL': '반도체 3배 (SOXL)',
        'TQQQ': '나스닥 3배 (TQQQ)'
    }
    df_us = pd.DataFrame(list(us_stocks.items()), columns=['Code', 'Name'])
    
    # 3. 합치기
    df_total = pd.concat([df_krx, df_us])
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

# --- 사이드바 ---
st.sidebar.title("🔍 분석 옵션")

# 종목 리스트
try:
    with st.spinner('종목 리스트 불러오는 중...'):
        df_stocks = get_stock_list()
    
    # 기본값 설정
    default_idx = 0
    matches = df_stocks.index[df_stocks['Code'] == '005930'].tolist()
    if matches:
        default_idx = matches[0]

    selected_label = st.sidebar.selectbox(
        "종목 검색", 
        df_stocks['Label'].values,
        index=default_idx if default_idx < len(df_stocks) else 0
    )
    ticker = selected_label.split('(')[-1].replace(')', '')

except:
    st.sidebar.error("리스트 로딩 실패. 직접 입력하세요.")
    ticker = st.sidebar.text_input("종목 코드", "005930")

# 경제 지표
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

# --- 데이터 로딩 함수 ---
@st.cache_data
def load_data(stock_code, fred_code, start):
    try:
        stock = fdr.DataReader(stock_code, start)
        fred = fdr.DataReader(fred_code, start)
        if stock.empty or fred.empty: return None
        df = pd.concat([stock['Close'], fred], axis=1).dropna()
        df.columns = ['Stock', 'Macro']
        return df
    except:
        return None

# --- 메인 화면 ---
st.title(f"📈 {ticker} vs {selected_name}")

df = load_data(ticker, selected_code, start_date)

if df is not None and not df.empty:
    # 정규화
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
    
    # 괴리율 계산
    gap = df['Stock_Norm'].iloc[-1] - df['Macro_Norm'].iloc[-1]
    
    # 1. 상단 지표 (Metric)
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 주가", f"{df['Stock'].iloc[-1]:,.0f}")
    col2.metric(f"지표 ({selected_name})", f"{df['Macro'].iloc[-1]:.2f}")
    
    # 2. 괴리율 상태 분석 및 텍스트 출력 (여기가 추가된 부분!)
    if gap > 0.5:
        state = "🔴 과열 구간"
        st.error(f"""
        **[경고] 주가가 경제 지표보다 과도하게 높습니다! (Gap: {gap:.2f})** 현재 주가가 실물 지표(펀더멘털)보다 훨씬 빠르게 올랐습니다. 
        단기적인 급등에 따른 '거품'일 가능성이 있으니 추격 매수에 주의하세요.
        """)
    elif gap < -0.5:
        state = "🔵 침체/저평가 구간"
        st.info(f"""
        **[기회?] 주가가 경제 지표보다 너무 낮습니다. (Gap: {gap:.2f})** 경제 상황에 비해 주가가 과도하게 하락한 상태입니다. 
        시장의 공포감이 반영되었거나, 저평가 매수 기회일 수 있습니다.
        """)
    else:
        state = "🟢 적정/동행 구간"
        st.success(f"""
        **[안정] 주가와 경제 지표가 비슷하게 움직입니다. (Gap: {gap:.2f})** 큰 괴리 없이 흐름을 잘 따라가고 있습니다. 
        특이한 징후보다는 시장의 추세를 따르는 중입니다.
        """)

    col3.metric("괴리율 상태", state, f"{gap:.2f}")

    # 3. 차트
    st.subheader("추세 비교 차트")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name=selected_name + ' (정규화)', line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("데이터를 불러올 수 없습니다.")
