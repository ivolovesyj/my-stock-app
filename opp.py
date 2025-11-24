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

st.sidebar.markdown("---") 
st.sidebar.subheader("📅 분석 기간 설정")
period_options = {
    "6개월": 180,
    "1년": 365,
    "2년": 730,
    "3년": 1095,
    "5년": 1825
}
selected_period = st.sidebar.radio(
    "기간을 선택하세요", 
    list(period_options.keys()), 
    index=2, 
    horizontal=True,
    label_visibility="collapsed"
)
days = period_options[selected_period]
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# --- 4. 데이터 로딩 (수정됨: 각각 따로 가져옴) ---
@st.cache_data
def load_data_separate(stock_code, fred_code, start):
    # 1. 주식 데이터 따로
    try:
        stock = fdr.DataReader(stock_code, start)
    except:
        stock = pd.DataFrame()
        
    # 2. 경제지표 데이터 따로
    try:
        fred = fdr.DataReader(fred_code, start)
    except:
        fred = pd.DataFrame()
        
    return stock, fred

# --- 5. 메인 화면 ---
st.title(f"📈 {display_name} vs {selected_name}")

# 데이터를 각각 받아옵니다 (Merge 안 하고)
stock_df, macro_df = load_data_separate(ticker, selected_code, start_date)

if not stock_df.empty and not macro_df.empty:
    
    # --- [핵심] 상단 숫자용 데이터 (무조건 최신값 사용) ---
    latest_stock_price = stock_df['Close'].iloc[-1]
    latest_stock_date = stock_df.index[-1].strftime('%Y-%m-%d')
    
    latest_macro_val = macro_df.iloc[-1].values[0] # FRED 데이터는 컬럼이 하나라 values[0]
    latest_macro_date = macro_df.index[-1].strftime('%Y-%m-%d')

    # --- 차트 & 괴리율용 데이터 (날짜 교집합 Merge) ---
    # 분석을 위해서는 날짜를 맞춰야 하므로 여기서 합칩니다.
    df_merged = pd.concat([stock_df['Close'], macro_df], axis=1).dropna()
    df_merged.columns = ['Stock', 'Macro']
    
    # 정규화 및 괴리율 계산 (Merge된 데이터 기준)
    df_merged['Stock_Norm'] = (df_merged['Stock'] - df_merged['Stock'].min()) / (df_merged['Stock'].max() - df_merged['Stock'].min())
    df_merged['Macro_Norm'] = (df_merged['Macro'] - df_merged['Macro'].min()) / (df_merged['Macro'].max() - df_merged['Macro'].min())
    gap = df_merged['Stock_Norm'].iloc[-1] - df_merged['Macro_Norm'].iloc[-1]
    
    # --- 화면 표시 ---
    is_krx = ticker.isdigit()
    exchange_rate_info = ""

    if is_krx:
        price_html = f"""
        <div style="font-size: 14px; color: gray; margin-bottom: -5px;">주가 ({latest_stock_date})</div>
        <div style="font-size: 32px; font-weight: bold;">{latest_stock_price:,.0f}원</div>
        """
    else:
        ex_rate, ex_date = get_exchange_rate()
        krw_price = latest_stock_price * ex_rate
        exchange_rate_info = f"💱 환율: {ex_rate:,.2f}원 ({ex_date})"
        price_html = f"""
        <div style="font-size: 14px; color: gray; margin-bottom: -5px;">주가 ({latest_stock_date})</div>
        <div style="font-size: 32px; font-weight: bold;">${latest_stock_price:,.2f}</div>
        <div style="font-size: 16px; color: #555; margin-top: -5px;">(약 {krw_price:,.0f}원)</div>
        """

    guide = indicator_guide.get(selected_name)
    unit = guide['unit'] if guide else ""
    macro_value_display = f"{latest_macro_val:,.2f} {unit}"

    col1, col2, col3 = st.columns(3)
    col1.markdown(price_html, unsafe_allow_html=True)
    
    # 지표 날짜도 따로 표시해줍니다. (주가 날짜와 다를 수 있음을 명시)
    col2.metric(f"지표 ({latest_macro_date})", macro_value_display)
    
    # 상태 결정
    if gap > 0.5:
        state = "🔴 과열 (조심!)"
    elif gap < -0.5:
        state = "🔵 침체 (기회?)"
    else:
        state = "🟢 적정 (동행)"

    tooltip_text = """
    🤔 정규화 (Normalization)란?
    단위가 다른 주가와 지표를 0~1 점수로 변환해 '추세'만 비교하는 것입니다.

    🐕 괴리율 (Gap)이란?
    경제(주인)와 주가(강아지)의 거리입니다.
    (+): 주가가 너무 앞서감 (과열)
    (-): 주가가 너무 뒤처짐 (저평가)
    """
    col3.metric("괴리율 상태", state, f"{gap:.2f}", help=tooltip_text)

    if exchange_rate_info:
        st.caption(exchange_rate_info)

    st.markdown("### 🤖 AI 분석 리포트")
    if gap > 0.5:
        st.error(f"**🚨 [경고] 과열 구간 (Gap: {gap:.2f})**\n\n주가가 경제 지표보다 너무 빠르게 올랐습니다. 단기 급등일 수 있으니 주의하세요.")
    elif gap < -0.5:
        st.info(f"**💎 [기회?] 침체/저평가 구간 (Gap: {gap:.2f})**\n\n경제 상황에 비해 주가가 과도하게 낮습니다. 저가 매수의 기회일 수 있습니다.")
    else:
        st.success(f"**✅ [안정] 적정/동행 구간 (Gap: {gap:.2f})**\n\n주가가 경제 지표의 흐름을 잘 따라가고 있습니다.")

    with st.expander("❓ 정규화와 괴리율이 무엇인가요? (용어 설명 보기)"):
        st.markdown("""
        ### 1. 정규화 (Normalization)란? 🤔
        주가(예: 100,000원)와 경제지표(예: 4.5%)는 단위가 달라서 직접 비교할 수가 없습니다.
        그래서 두 데이터를 똑같이 **0점(최저) ~ 1점(최고)** 사이의 점수로 변환해서, **'추세(Trend)'만 비교하는 기술**입니다.
        
        ---
        
        ### 2. 괴리율 (Gap)이란? 🐕
        유명한 투자자 앙드레 코스톨라니는 **'경제는 주인이고, 주가는 강아지다'**라고 했습니다.
        * **괴리율이 크다 (+):** 강아지가 주인보다 너무 멀리 앞서갔습니다. (주가 과열)
        * **괴리율이 작다 (-):** 강아지가 주인보다 너무 뒤쳐졌습니다. (주가 저평가)
        """)

    if guide:
        with st.expander(f"💡 '{selected_name}' 투자 포인트 읽어보기", expanded=False):
            st.markdown(f"**[{guide['desc']}]**\n\n{guide['relation']} \n\n 👉 **Tip:** {guide['tip']}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['Macro_Norm'], name=selected_name, line=dict(color='red', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error(f"'{ticker}' 데이터를 찾을 수 없습니다. (혹은 경제 지표 데이터 로딩 실패)")
