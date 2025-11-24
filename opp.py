import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="내 손안의 퀀트", layout="wide")

# --- 1. 데이터 캐싱 ---
@st.cache_data
def get_stock_list():
    try:
        # 한국 주식 (KRX)
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx[['Code', 'Name']]
    except:
        df_krx = pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']})

    # 미국 주식 (S&P 500 + 주요 인기 ETF/종목)
    us_stocks = {
        'AAPL': '애플 (Apple)', 'NVDA': '엔비디아 (NVIDIA)', 'TSLA': '테슬라 (Tesla)',
        'MSFT': '마이크로소프트 (Microsoft)', 'GOOGL': '구글 (Alphabet)',
        'AMZN': '아마존 (Amazon)', 'META': '메타 (Meta)', 'NFLX': '넷플릭스 (Netflix)',
        'AMD': 'AMD', 'INTC': '인텔 (Intel)', 'QQQ': '나스닥 ETF (QQQ)',
        'SPY': 'S&P500 ETF (SPY)', 'SOXL': '반도체 3배 (SOXL)', 'TQQQ': '나스닥 3배 (TQQQ)',
        'O': '리얼티인컴 (Realty Income)', 'PLTR': '팔란티어 (Palantir)', 'IONQ': '아이온큐 (IonQ)',
        'JEPI': 'JP모건 커버드콜 (JEPI)', 'SCHD': '슈왑 배당 성장 (SCHD)'
    }
    df_us = pd.DataFrame(list(us_stocks.items()), columns=['Code', 'Name'])
    
    df_total = pd.concat([df_krx, df_us])
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

# --- 2. 지표별 가이드 ---
indicator_guide = {
    "미국 10년물 국채금리": {"desc": "전 세계 자산의 기준이 되는 '돈의 몸값'", "relation": "📉 역의 관계 (금리↑ 주가↓)", "tip": "금리가 오르면 안전한 채권으로 돈이 쏠려 주식(특히 기술주)엔 악재입니다."},
    "원/달러 환율": {"desc": "달러 1개를 사기 위한 한국 돈의 액수", "relation": "📉 역의 관계 (환율↑ 코스피↓)", "tip": "환율 급등은 외국인 자금 이탈을 부릅니다. 단, 수출 기업에겐 호재일 수 있습니다."},
    "국제유가(WTI)": {"desc": "에너지 비용을 대표하는 원유 가격", "relation": "⚠️ 케이스 바이 케이스", "tip": "수요 증가로 오르면 호재, 공급 부족(전쟁)으로 급등하면 비용 증가 악재입니다."},
    "나스닥 지수": {"desc": "미국 기술주 중심의 시장 지수", "relation": "🤝 양의 관계 (동행)", "tip": "한국 주식 시장은 미국 나스닥의 흐름을 강하게 추종합니다."},
    "S&P 500 지수": {"desc": "미국 우량주 500개 지수", "relation": "🤝 양의 관계 (동행)", "tip": "글로벌 증시의 표준입니다. 이 지수가 꺾이면 전 세계가 위험합니다."},
    "미국 기준금리": {"desc": "미국 연준(Fed)의 정책 금리", "relation": "📉 역의 관계", "tip": "돈줄을 죄는 신호입니다. 금리 인상은 주식 시장에 하락 압력을 줍니다."}
}

# --- 3. 사이드바 ---
st.sidebar.title("🔍 분석 옵션")

# A. 리스트에서 찾기
try:
    with st.spinner('종목 리스트 로딩 중...'):
        df_stocks = get_stock_list()
    
    default_idx = 0
    if '005930' in df_stocks['Code'].values:
         default_idx = df_stocks.index[df_stocks['Code'] == '005930'].tolist()[0]

    # [수정] help 파라미터 추가 (물음표 설명)
    selected_label = st.sidebar.selectbox(
        "1. 리스트에서 검색", 
        df_stocks['Label'].values,
        index=default_idx if default_idx < len(df_stocks) else 0,
        help="🚀 웹사이트 속도를 위해 '한국 전 종목'과 '미국 S&P500/인기주'만 리스트에 담았습니다. 여기에 없는 종목은 아래 '직접 입력' 칸을 이용해주세요!"
    )
    ticker_from_list = selected_label.split('(')[-1].replace(')', '')

except:
    ticker_from_list = "005930"

# B. 직접 입력하기
st.sidebar.markdown("---") 
# [수정] help 파라미터 추가
custom_ticker = st.sidebar.text_input(
    "2. 직접 입력 (티커)", 
    "",
    placeholder="예: PLTR, JEPI, XOM",
    help="💡 리스트에 없는 미국 주식이나 ETF는 여기에 티커(Symbol)만 적으시면 됩니다. (예: 팔란티어 -> PLTR)"
)

if custom_ticker:
    ticker = custom_ticker.upper()
    display_name = ticker
else:
    ticker = ticker_from_list
    display_name = selected_label.split('(')[0]

# --- 설정 계속 ---
indicators = {
    "미국 10년물 국채금리": "FRED:DGS10", "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO", "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500", "미국 기준금리": "FRED:FEDFUNDS"
}
selected_name = st.sidebar.selectbox("비교할 경제지표", list(indicators.keys()))
selected_code = indicators[selected_name]

days = st.sidebar.slider("분석 기간(일)", 365, 1825, 730)
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- 4. 데이터 로딩 ---
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

# --- 5. 메인 화면 ---
st.title(f"📈 {display_name} vs {selected_name}")

df = load_data(ticker, selected_code, start_date)

if df is not None and not df.empty:
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
    gap = df['Stock_Norm'].iloc[-1] - df['Macro_Norm'].iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 주가", f"{df['Stock'].iloc[-1]:,.0f}")
    col2.metric(f"지표 ({selected_name})", f"{df['Macro'].iloc[-1]:.2f}")
    
    if gap > 0.5:
        state = "🔴 과열 (조심!)"
        msg = "주가가 지표보다 너무 높습니다. 단기 급등 주의!"
    elif gap < -0.5:
        state = "🔵 침체 (기회?)"
        msg = "주가가 지표보다 너무 낮습니다. 저평가 가능성!"
    else:
        state = "🟢 적정 (동행)"
        msg = "지표와 비슷하게 움직이고 있습니다."
        
    col3.metric("괴리율 상태", state, f"{gap:.2f}")

    guide = indicator_guide.get(selected_name)
    if guide:
        with st.expander(f"💡 '{selected_name}' 투자 포인트 확인하기", expanded=True):
            st.markdown(f"**[{guide['desc']}]**\n\n{guide['relation']} \n\n 👉 **Tip:** {guide['tip']}")
        st.info(f"📢 AI 코멘트: {msg}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name=selected_name, line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"'{ticker}' 데이터를 찾을 수 없습니다. 티커를 확인해주세요.")
    st.caption("예: 애플(AAPL), 팔란티어(PLTR) / 삼성전자(005930)")
