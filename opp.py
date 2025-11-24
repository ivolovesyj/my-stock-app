import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="나만의 퀀트 모델", layout="wide")

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
    
    # 외부 데이터 로딩 시도 (실패시 base만 사용)
    df_krx = pd.DataFrame()
    df_sp500 = pd.DataFrame()
    try:
        df_krx = fdr.StockListing('KRX')[['Code', 'Name']]
    except: pass
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
    except: pass

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

# --- 2. 사이드바 (종목 선택) ---
st.sidebar.title("🔍 분석 옵션")

with st.spinner('리스트 로딩 중...'):
    df_stocks = get_stock_list()

default_idx = 0
if '005930' in df_stocks['Code'].values:
    default_idx = df_stocks.index[df_stocks['Code'] == '005930'].tolist()[0]

selected_label = st.sidebar.selectbox("1. 종목 선택", df_stocks['Label'].values, index=default_idx)
ticker_from_list = selected_label.split('(')[-1].replace(')', '')

st.sidebar.markdown("---")
custom_ticker = st.sidebar.text_input("2. 직접 입력 (티커)", "", placeholder="예: JEPI")

if custom_ticker:
    ticker = custom_ticker.upper()
    display_name = ticker
else:
    ticker = ticker_from_list
    display_name = selected_label.split('(')[0]

# --- 3. [NEW] 복합 지표 설정 (Multi-Select) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 경제지표 믹싱 (Mixing)")

indicators_map = {
    "미국 10년물 금리": "FRED:DGS10", 
    "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO", 
    "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500", 
    "미국 기준금리": "FRED:FEDFUNDS",
    "달러 인덱스": "FRED:DTWEXBGS",
    "VIX (공포지수)": "FRED:VIXCLS"
}

# 다중 선택 박스
selected_indicators = st.sidebar.multiselect(
    "지표를 여러 개 선택하세요",
    list(indicators_map.keys()),
    default=["미국 10년물 금리", "원/달러 환율"] # 기본값
)

# 선택한 지표별 가중치/방향 설정
configs = {}
if selected_indicators:
    st.sidebar.caption("👇 지표별 비중과 방향을 설정하세요")
    for name in selected_indicators:
        with st.sidebar.expander(f"⚙️ {name} 설정", expanded=True):
            # 가중치 (0~10)
            weight = st.slider(f"중요도 (비중)", 0.0, 10.0, 5.0, key=f"w_{name}")
            # 역방향 여부 (금리, 환율 등은 보통 역방향)
            is_inverse = st.checkbox(f"역방향(Inverse) 적용?", value=False, key=f"inv_{name}", 
                                     help="체크하면 수치가 낮을수록 점수가 높아집니다. (예: 환율/금리가 내리면 주가에 좋다)")
            configs[name] = {'code': indicators_map[name], 'weight': weight, 'inverse': is_inverse}

# 분석 기간
st.sidebar.markdown("---")
period_options = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
selected_period = st.sidebar.radio("기간", list(period_options.keys()), index=2, horizontal=True)
start_date = (datetime.now() - timedelta(days=period_options[selected_period])).strftime('%Y-%m-%d')

# --- 4. 데이터 로딩 및 계산 ---
@st.cache_data
def load_data_mix(stock_code, configs, start):
    # 1. 주가 로딩
    try:
        stock = fdr.DataReader(stock_code, start)['Close']
    except:
        return None, None, None

    # 2. 경제지표 로딩 & 합성
    macro_score = pd.Series(0, index=stock.index) # 0으로 채운 빈 시리즈
    total_weight = 0
    loaded_indicators = {} # 개별 지표 저장용

    for name, conf in configs.items():
        try:
            # 지표 가져오기
            data = fdr.DataReader(conf['code'], start)
            if data.empty: continue
            
            # 주가 날짜에 맞춰 정렬 (reindex) - 보간법 사용
            # ffill: 앞의 데이터로 채움 (주말/공휴일 등)
            aligned_data = data.iloc[:, 0].reindex(stock.index, method='ffill')
            loaded_indicators[name] = aligned_data # 나중에 쓰려고 저장

            # 정규화 (0~1)
            norm = (aligned_data - aligned_data.min()) / (aligned_data.max() - aligned_data.min())
            
            # 역방향 처리 (체크했으면 1에서 뺌)
            if conf['inverse']:
                norm = 1 - norm
            
            # 가중치 적용 합산
            macro_score = macro_score.add(norm * conf['weight'], fill_value=0)
            total_weight += conf['weight']
            
        except:
            pass
            
    # 최종 점수 산출 (가중 평균)
    if total_weight > 0:
        final_macro_index = macro_score / total_weight
    else:
        final_macro_index = pd.Series(0, index=stock.index)

    return stock, final_macro_index, loaded_indicators

# --- 5. 메인 화면 ---
composite_name = "나만의 매크로 지수 (Custom Macro Index)"
st.title(f"📈 {display_name} vs {composite_name}")

if not selected_indicators:
    st.warning("👈 사이드바에서 경제지표를 최소 1개 이상 선택해주세요.")
else:
    stock_series, macro_series, raw_indicators = load_data_mix(ticker, configs, start_date)

    if stock_series is not None and not stock_series.empty:
        # 데이터 정리 (NaN 제거)
        df_final = pd.concat([stock_series, macro_series], axis=1).dropna()
        df_final.columns = ['Stock', 'Macro_Index']

        # 정규화 (차트 비교용)
        df_final['Stock_Norm'] = (df_final['Stock'] - df_final['Stock'].min()) / (df_final['Stock'].max() - df_final['Stock'].min())
        # 매크로 지수는 이미 정규화되어 있지만, 확실하게 0~1로 다시 맞춤 (시각적 통일)
        df_final['Macro_Norm'] = (df_final['Macro_Index'] - df_final['Macro_Index'].min()) / (df_final['Macro_Index'].max() - df_final['Macro_Index'].min())
        
        gap = df_final['Stock_Norm'].iloc[-1] - df_final['Macro_Norm'].iloc[-1]
        last_date = df_final.index[-1].strftime('%Y-%m-%d')

        # --- 상단 메트릭 ---
        is_krx = ticker.isdigit()
        if is_krx:
            price_html = f"<div style='font-size:28px; font-weight:bold;'>{df_final['Stock'].iloc[-1]:,.0f}원</div>"
        else:
            ex_rate, _ = get_exchange_rate()
            krw = df_final['Stock'].iloc[-1] * ex_rate
            price_html = f"<div style='font-size:28px; font-weight:bold;'>${df_final['Stock'].iloc[-1]:,.2f}</div><div style='font-size:14px; color:gray;'>(약 {krw:,.0f}원)</div>"

        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**주가 ({last_date})**<br>{price_html}", unsafe_allow_html=True)
        col2.metric(f"나만의 매크로 점수 (0~1점)", f"{df_final['Macro_Index'].iloc[-1]:.2f} 점")

        if gap > 0.3: state = "🔴 주가가 더 높음 (과열?)"
        elif gap < -0.3: state = "🔵 지수가 더 높음 (저평가?)"
        else: state = "🟢 균형 (동행)"
        
        col3.metric("괴리율 상태", state, f"{gap:.2f}", help="양수: 주가가 내 지수보다 높음 / 음수: 주가가 내 지수보다 낮음")

        # --- 상세 설정 정보 표시 ---
        st.info("💡 **현재 적용된 지표 구성:** " + ", ".join([f"{k}(x{v['weight']})" + ("🔄역" if v['inverse'] else "") for k,v in configs.items()]))

        # --- 차트 그리기 ---
        fig = go.Figure()
        # 1. 주가
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue', width=2)))
        # 2. 합성 지표
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Macro_Norm'], name='내 매크로 지수', line=dict(color='red', width=2, dash='dot')))
        st.plotly_chart(fig, use_container_width=True)

        # --- [추가 기능] 개별 지표 열람 ---
        with st.expander("📊 합치기 전, 개별 지표들의 값 보기"):
            # 데이터프레임으로 만들어서 보여줌
            indi_df = pd.DataFrame(raw_indicators)
            st.dataframe(indi_df.tail(10).style.format("{:,.2f}"))
            
        with st.expander("❓ '역방향(Inverse)'이 뭔가요?"):
             st.markdown("""
             - **정방향:** 지표가 오르면 주가에도 좋다. (예: 나스닥 지수, S&P500)
             - **역방향(Inverse):** 지표가 오르면 주가에는 나쁘다. (예: 환율, 금리, 유가)
             
             여러 지표를 합칠 때, 성격이 반대인 것들을 그냥 더하면 서로 상쇄되어 0이 될 수 있습니다.
             그래서 **주가에 안 좋은 지표(역방향)는 뒤집어서(1 - 값)** 더해야 올바른 **'투자 매력도 점수'**가 나옵니다.
             """)

    else:
        st.error("데이터 로딩 실패. 종목 코드나 날짜를 확인해주세요.")
