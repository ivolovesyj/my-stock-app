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
    base_data = [
        {'Code': '005930', 'Name': '삼성전자'},
        {'Code': '000660', 'Name': 'SK하이닉스'},
        {'Code': '005380', 'Name': '현대차'},
        {'Code': '035420', 'Name': 'NAVER'},
        {'Code': '035720', 'Name': '카카오'},
        {'Code': 'AAPL', 'Name': '애플 (Apple)'},
        {'Code': 'NVDA', 'Name': '엔비디아 (NVIDIA)'},
        {'Code': 'TSLA', 'Name': '테슬라 (Tesla)'},
        {'Code': 'MSFT', 'Name': '마이크로소프트 (Microsoft)'},
        {'Code': 'GOOGL', 'Name': '구글 (Alphabet)'},
        {'Code': 'AMZN', 'Name': '아마존 (Amazon)'},
        {'Code': 'DIS', 'Name': '월트 디즈니 (Disney)'},
        {'Code': 'KO', 'Name': '코카콜라 (Coca-Cola)'},
        {'Code': 'SBUX', 'Name': '스타벅스 (Starbucks)'},
        {'Code': 'O', 'Name': '리얼티인컴 (Realty Income)'},
        {'Code': 'QQQ', 'Name': '나스닥 100 (QQQ)'},
        {'Code': 'SPY', 'Name': 'S&P 500 (SPY)'},
        {'Code': 'SCHD', 'Name': '슈왑 배당 (SCHD)'},
        {'Code': 'JEPI', 'Name': 'JP모건 커버드콜 (JEPI)'},
        {'Code': 'PLTR', 'Name': '팔란티어 (Palantir)'},
        {'Code': 'IONQ', 'Name': '아이온큐 (IonQ)'}
    ]
    df_base = pd.DataFrame(base_data)

    df_krx = pd.DataFrame()
    df_sp500 = pd.DataFrame()

    try:
        df_krx = fdr.StockListing('KRX')[['Code', 'Name']]
    except:
        pass

    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df_sp500 = pd.read_csv(url)[['Symbol', 'Name']]
        df_sp500.columns = ['Code', 'Name']
        korean_map = {'AAPL':'애플', 'NVDA':'엔비디아', 'TSLA':'테슬라', 'MSFT':'마이크로소프트', 'GOOGL':'구글', 'AMZN':'아마존', 'META':'메타', 'NFLX':'넷플릭스'}
        for code, kor in korean_map.items():
             mask = df_sp500['Code'] == code
             if mask.any():
                 eng = df_sp500.loc[mask, 'Name'].values[0]
                 df_sp500.loc[mask, 'Name'] = f"{kor} ({eng})"
    except:
        pass

    df_total = pd.concat([df_base, df_krx, df_sp500]).drop_duplicates(subset=['Code'])
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

@st.cache_data
def get_exchange_rate():
    try:
        df = fdr.DataReader('USD/KRW', (datetime.now() - timedelta(days=7)))
        return df['Close'].iloc[-1], df.index[-1].strftime('%Y-%m-%d')
    except:
        return 1400.0, datetime.now().strftime('%Y-%m-%d')

# --- 2. 지표 가이드 ---
indicator_guide = {
    "미국 10년물 국채금리": {"desc": "전 세계 자산의 기준이 되는 '돈의 몸값'", "relation": "📉 역의 관계 (금리↑ 주가↓)", "tip": "금리가 오르면 안전한 채권으로 돈이 쏠려 주식(특히 기술주)엔 악재입니다.", "unit": "%"},
    "원/달러 환율": {"desc": "달러 1개를 사기 위한 한국 돈의 액수", "relation": "📉 역의 관계 (환율↑ 코스피↓)", "tip": "환율 급등은 외국인 자금 이탈을 부릅니다. 단, 수출 기업에겐 호재일 수 있습니다.", "unit": "원"},
    "국제유가(WTI)": {"desc": "에너지 비용을 대표하는 원유 가격", "relation": "⚠️ 케이스 바이 케이스", "tip": "수요 증가로 오르면 호재, 공급 부족(전쟁)으로 급등하면 비용 증가 악재입니다.", "unit": "달러($)"},
    "나스닥 지수": {"desc": "미국 기술주 중심의 시장 지수", "relation": "🤝 양의 관계 (동행)", "tip": "한국 주식 시장은 미국 나스닥의 흐름을 강하게 추종합니다.", "unit": "pt"},
    "S&P 500 지수": {"desc": "미국 우량주 500개 지수", "relation": "🤝 양의 관계 (동행)", "tip": "글로벌 증시의 표준입니다. 이 지수가 꺾이면 전 세계가 위험합니다.", "unit": "pt"},
    "미국 기준금리": {"desc": "미국 연준(Fed)의 정책 금리", "relation": "📉 역의 관계", "tip": "돈줄을 죄는 신호입니다. 금리 인상은 주식 시장에 하락 압력을 줍니다.", "unit": "%"}
}

# --- 3. 사이드바 ---
st.sidebar.title("🔍 분석 옵션")

with st.spinner('종목 리스트 준비 중...'):
    df_stocks = get_stock_list()

default_idx = 0
if '005930' in df_stocks['Code'].values:
    default_idx = df_stocks.index[df_stocks['Code'] == '005930'].tolist()[0]

selected_label = st.sidebar.selectbox(
    "1. 리스트에서 검색", 
    df_stocks['Label'].values,
    index=default_idx if default_idx < len(df_stocks) else 0,
    help="기본 VIP 종목 + KRX + S&P500이 포함되어 있습니다."
)
ticker_from_list = selected_label.split('(')[-1].replace(')', '')

st.sidebar.markdown("---") 
custom_ticker = st.sidebar.text_input(
    "2. 직접 입력 (티커)", 
    "",
    placeholder="예: JEPI, SCHD",
    help="리스트에 없는 종목은 여기에 티커를 입력하세요."
)

if custom_ticker:
    ticker = custom_ticker.upper()
    display_name = ticker
else:
    ticker = ticker_from_list
    display_name = selected_label.split('(')[0]

indicators = {
    "미국 10년물 국채금리": "FRED:DGS10", "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO", "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500", "미국 기준금리": "FRED:FEDFUNDS"
}
selected_name = st.sidebar.selectbox("비교할 경제지표", list(indicators.keys()))
selected_code = indicators[selected_name]

# --- [수정 2] 분석 기간을 년 단위 버튼으로 변경 ---
st.sidebar.markdown("---") 
st.sidebar.subheader("📅 분석 기간 설정")
period_options = {
    "6개월": 180,
    "1년": 365,
    "2년": 730,
    "3년": 1095,
    "5년": 1825
}
# 가로형 버튼(pills 느낌)으로 선택
selected_period = st.sidebar.radio(
    "기간을 선택하세요", 
    list(period_options.keys()), 
    index=2, # 기본값 2년
    horizontal=True,
    label_visibility="collapsed"
)
days = period_options[selected_period]
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
    
    last_date = df.index[-1].strftime('%Y-%m-%d')
    current_price = df['Stock'].iloc[-1]
    is_krx = ticker.isdigit()
    exchange_rate_info = ""

    # --- [수정 1] 주가 표시를 HTML로 커스텀 (잘림 방지) ---
    if is_krx:
        # 한국 주식
        price_html = f"""
        <div style="font-size: 14px; color: gray; margin-bottom: -5px;">주가 (종가 기준, {last_date})</div>
        <div style="font-size: 32px; font-weight: bold;">{current_price:,.0f}원</div>
        """
    else:
        # 미국 주식 (줄바꿈 및 작은 글씨 적용)
        ex_rate, ex_date = get_exchange_rate()
        krw_price = current_price * ex_rate
        exchange_rate_info = f"💱 환율: {ex_rate:,.2f}원 ({ex_date})"
        price_html = f"""
        <div style="font-size: 14px; color: gray; margin-bottom: -5px;">주가 (종가 기준, {last_date})</div>
        <div style="font-size: 32px; font-weight: bold;">${current_price:,.2f}</div>
        <div style="font-size: 16px; color: #555; margin-top: -5px;">(약 {krw_price:,.0f}원)</div>
        """

    # 지표 값
    guide = indicator_guide.get(selected_name)
    unit = guide['unit'] if guide else ""
    macro_value_display = f"{df['Macro'].iloc[-1]:,.2f} {unit}"

    col1, col2, col3 = st.columns(3)
    
    # col1: 주가 (커스텀 HTML 사용)
    col1.markdown(price_html, unsafe_allow_html=True)
    
    # col2: 지표 (기존 방식)
    col2.metric(f"지표 (종가 기준, {last_date})", macro_value_display)
    
    # col3: 괴리율 상태 + [수정 3] 툴팁(?)에 설명 넣기
    if gap > 0.5:
        state = "🔴 과열 (조심!)"
        msg = "주가가 지표보다 너무 높습니다. 단기 급등 주의!"
    elif gap < -0.5:
        state = "🔵 침체 (기회?)"
        msg = "주가가 지표보다 너무 낮습니다. 저평가 가능성!"
    else:
        state = "🟢 적정 (동행)"
        msg = "지표와 비슷하게 움직이고 있습니다."
    
    # 여기가 핵심! help 파라미터에 긴 설명을 넣었습니다.
    tooltip_text = """
    🤔 정규화 (Normalization)란?
    서로 단위가 다른 주가와 지표를 0~1 사이 점수로 변환해 '추세'만 비교하는 것입니다.

    🐕 괴리율 (Gap)이란?
    '경제(주인)와 주가(강아지)' 이론입니다.
    - 양수(+)가 크면: 강아지가 너무 앞서감 (과열)
    - 음수(-)가 크면: 강아지가 뒤처짐 (저평가)
    """
    col3.metric("괴리율 상태", state, f"{gap:.2f}", help=tooltip_text)

    # 환율 정보 표시
    if exchange_rate_info:
        st.caption(exchange_rate_info)

    # 투자 포인트 (기존 하단 설명)
    if guide:
        with st.expander(f"💡 '{selected_name}' 투자 포인트 확인하기", expanded=True):
            st.markdown(f"**[{guide['desc']}]**\n\n{guide['relation']} \n\n 👉 **Tip:** {guide['tip']}")
        st.info(f"📢 AI 코멘트: {msg}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['Macro_Norm'], name=selected_name, line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"'{ticker}' 데이터를 찾을 수 없습니다.")
    st.write("1. 티커(코드)가 정확한지 확인해주세요.")
    st.write("2. 미국 주식이라면 직접 입력 창을 이용해보세요.")
