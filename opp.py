import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="내 손안의 퀀트", layout="wide")

# --- 사이드바 ---
st.sidebar.title("🔍 분석 옵션")
ticker = st.sidebar.text_input("종목 코드 (예: 005930, AAPL)", value="005930")

# FRED 데이터 코드로 변경 (FinanceDataReader 사용)
indicators = {
    "미국 10년물 국채금리": "FRED:DGS10",
    "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO",
    "나스닥 지수": "FRED:NASDAQCOM"
}
selected_name = st.sidebar.selectbox("비교할 경제지표", list(indicators.keys()))
selected_code = indicators[selected_name]

days = st.sidebar.slider("분석 기간(일)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- 데이터 로딩 함수 ---
@st.cache_data
def load_data(stock_code, fred_code, start):
    # 1. 주식 데이터
    stock = fdr.DataReader(stock_code, start)
    # 2. 경제 지표 데이터 (fdr로 통합)
    fred = fdr.DataReader(fred_code, start)
    
    # 데이터 병합
    df = pd.concat([stock['Close'], fred], axis=1).dropna()
    df.columns = ['Stock', 'Macro']
    return df

# --- 메인 화면 ---
st.title(f"📈 {ticker} vs {selected_name}")

try:
    df = load_data(ticker, selected_code, start_date)
    
    # 정규화
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
    
    # 괴리율
    gap = df['Stock_Norm'].iloc[-1] - df['Macro_Norm'].iloc[-1]
    
    # 지표 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 주가", f"{df['Stock'].iloc[-1]:,.0f}")
    col2.metric("지표 값", f"{df['Macro'].iloc[-1]:.2f}")
    
    state = "⚠️ 과열/괴리" if abs(gap) > 0.5 else "✅ 안정/동조"
    col3.metric("괴리율 상태", state, f"{gap:.2f}")

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가(정규화)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name='경제지표(정규화)', line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터 오류: {e}")
    st.info("티커가 정확한지 확인해주세요.")
