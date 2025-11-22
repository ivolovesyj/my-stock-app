import streamlit as st
import FinanceDataReader as fdr
import pandas_datareader.data as web
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 기본 설정
st.set_page_config(page_title="내 손안의 퀀트", layout="wide")

# --- 사이드바: 옵션 설정 ---
st.sidebar.title("🔍 분석 옵션")
ticker = st.sidebar.text_input("종목 코드 입력 (예: 005930, AAPL)", value="005930")

# 경제 지표 리스트
indicators = {
    "미국 10년물 국채금리": "DGS10",
    "원/달러 환율": "DEXKOUS",
    "국제유가(WTI)": "DCOILWTICO",
    "나스닥 지수": "NASDAQCOM"
}
selected_indi = st.sidebar.selectbox("비교할 경제지표", list(indicators.keys()))

days = st.sidebar.slider("분석 기간(일)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- 데이터 로딩 함수 ---
@st.cache_data
def load_data(code, indi_code, start):
    stock = fdr.DataReader(code, start)
    indi = web.DataReader(indi_code, 'fred', start)
    df = pd.concat([stock['Close'], indi], axis=1).dropna()
    df.columns = ['Stock', 'Macro']
    return df

# --- 메인 화면 ---
st.title(f"📈 {ticker} vs {selected_indi} 분석")

try:
    # 데이터 가져오기
    df = load_data(ticker, indicators[selected_indi], start_date)
    
    # 정규화 (0~1 변환)
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
    
    # 괴리율 계산
    gap = df['Stock_Norm'].iloc[-1] - df['Macro_Norm'].iloc[-1]
    
    # 1. 핵심 지표 보여주기
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 주가", f"{df['Stock'].iloc[-1]:,.0f}")
    col2.metric(f"{selected_indi}", f"{df['Macro'].iloc[-1]:.2f}")
    
    if abs(gap) > 0.5:
        state = "⚠️ 과열/괴리 심각"
    else:
        state = "✅ 안정/동조화"
        
    col3.metric("괴리율 판단", state, f"Gap: {gap:.2f}")
    
    # 2. 차트 그리기
    st.subheader("주가 vs 경제지표 추세 비교")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가(정규화)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name='경제지표(정규화)', line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("파란 선(주가)과 빨간 점선(경제지표)의 차이가 벌어질수록 고평가/저평가 판단의 근거가 됩니다.")

except Exception as e:
    st.error("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")