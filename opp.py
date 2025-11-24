import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="내 손안의 퀀트", layout="wide")

# --- 1. 데이터 캐싱 (속도 향상) ---
@st.cache_data
def get_stock_list():
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx[['Code', 'Name']]
    except:
        df_krx = pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']})

    us_stocks = {
        'AAPL': '애플 (Apple)', 'NVDA': '엔비디아 (NVIDIA)', 'TSLA': '테슬라 (Tesla)',
        'MSFT': '마이크로소프트 (Microsoft)', 'GOOGL': '구글 (Alphabet)',
        'AMZN': '아마존 (Amazon)', 'META': '메타 (Meta)', 'NFLX': '넷플릭스 (Netflix)',
        'AMD': 'AMD', 'INTC': '인텔 (Intel)', 'QQQ': '나스닥 ETF (QQQ)',
        'SPY': 'S&P500 ETF (SPY)', 'SOXL': '반도체 3배 (SOXL)', 'TQQQ': '나스닥 3배 (TQQQ)'
    }
    df_us = pd.DataFrame(list(us_stocks.items()), columns=['Code', 'Name'])
    
    df_total = pd.concat([df_krx, df_us])
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

# --- 2. 지표별 설명 가이드 (딕셔너리) ---
# 여기가 핵심입니다! 지표별로 보여줄 설명을 미리 적어둡니다.
indicator_guide = {
    "미국 10년물 국채금리": {
        "desc": "전 세계 자산 가격의 기준이 되는 '돈의 몸값'입니다.",
        "relation": "📉 역의 관계 (금리↑ 주가↓)",
        "tip": "금리가 오르면 안전한 채권으로 돈이 몰려 주식 시장엔 악재입니다. 특히 기술주(성장주)가 타격을 크게 받습니다."
    },
    "원/달러 환율": {
        "desc": "달러 1개를 사기 위해 필요한 한국 돈(원화)의 액수입니다.",
        "relation": "📉 역의 관계 (환율↑ 코스피↓)",
        "tip": "환율 급등(원화 가치 하락)은 외국인 투자자가 한국 주식을 팔고 떠나게 만듭니다. 단, 자동차 등 수출 기업에겐 호재일 수 있습니다."
    },
    "국제유가(WTI)": {
        "desc": "서부 텍사스산 원유 가격으로, 에너지 비용을 대표합니다.",
        "relation": "⚠️ 케이스 바이 케이스",
        "tip": "경기가 좋아 수요가 늘어 오르는 건 괜찮지만, 전쟁 등으로 공급이 막혀 급등하면 기업 비용이 늘어나 주가에 나쁩니다."
    },
    "나스닥 지수": {
        "desc": "미국의 대표 기술주들이 모여있는 시장 지수입니다.",
        "relation": "🤝 양의 관계 (동행)",
        "tip": "한국 주식은 미국 기술주 흐름을 따라가는 경향이 강합니다. 나스닥이 밤새 폭락하면 한국 장도 아침에 하락할 확률이 높습니다."
    },
    "S&P 500 지수": {
        "desc": "미국 시장을 대표하는 500개 우량 기업의 지수입니다.",
        "relation": "🤝 양의 관계 (동행)",
        "tip": "전 세계 주식 시장의 표준입니다. 이 지수가 꺾이면 전 세계 투자 심리가 얼어붙습니다."
    },
    "미국 기준금리": {
        "desc": "미국 중앙은행(Fed)이 결정하는 초단기 정책 금리입니다.",
        "relation": "📉 역의 관계 (시차 존재)",
        "tip": "수도꼭지와 같습니다. 금리를 올리면 시중의 돈줄이 말라 주가가 하락 압력을 받습니다."
    }
}

# --- 3. 사이드바 설정 ---
st.sidebar.title("🔍 분석 옵션")

try:
    with st.spinner('종목 리스트 로딩 중...'):
        df_stocks = get_stock_list()
    
    default_idx = 0
    matches = df_stocks.index[df_stocks['Code'] == '005930'].tolist()
    if matches: default_idx = matches[0]

    selected_label = st.sidebar.selectbox("종목 검색", df_stocks['Label'].values, index=default_idx if default_idx < len(df_stocks) else 0)
    ticker = selected_label.split('(')[-1].replace(')', '')

except:
    st.sidebar.error("리스트 로딩 실패")
    ticker = st.sidebar.text_input("종목 코드", "005930")

# 지표 선택 (가이드 딕셔너리의 키와 일치시켜야 함)
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
st.title(f"📈 {ticker} vs {selected_name}")

df = load_data(ticker, selected_code, start_date)

if df is not None and not df.empty:
    # 정규화
    df['Stock_Norm'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
    df['Macro_Norm'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
    
    gap = df['Stock_Norm'].iloc[-1] - df['Macro_Norm'].iloc[-1]
    
    # [상단] 주요 지표 3개 출력
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 주가", f"{df['Stock'].iloc[-1]:,.0f}")
    col2.metric(f"{selected_name}", f"{df['Macro'].iloc[-1]:.2f}")
    
    # 괴리율 상태 판단
    if gap > 0.5:
        gap_state = "🔴 과열 (조심!)"
        gap_msg = "주가가 지표보다 너무 높아요. 단기 급등일 수 있습니다."
    elif gap < -0.5:
        gap_state = "🔵 침체 (기회?)"
        gap_msg = "주가가 지표보다 너무 낮아요. 저평가 상태일 수 있습니다."
    else:
        gap_state = "🟢 적정 (동행)"
        gap_msg = "큰 괴리 없이 흐름을 잘 따라가고 있습니다."
        
    col3.metric("괴리율 상태", gap_state, f"{gap:.2f}")

    # --- [핵심] 지표 설명 박스 (사용자 요청 위치) ---
    # 수치 바로 아래에 깔끔한 설명 박스를 배치합니다.
    guide = indicator_guide.get(selected_name, None)
    
    if guide:
        with st.expander(f"💡 '{selected_name}'의 투자 포인트 읽기 (Click)", expanded=True):
            st.markdown(f"""
            - **의미:** {guide['desc']}
            - **공식:** **{guide['relation']}**
            - **해석:** {guide['tip']}
            """)
        st.caption(f"📢 {gap_msg}") # 괴리율에 대한 한줄 평도 여기에 추가

    # 차트 그리기
    st.subheader("추세 비교 차트")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name=selected_name + ' (정규화)', line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("데이터를 가져오지 못했습니다. 종목 코드나 날짜를 확인해주세요.")
