import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 페이지 설정 & 디자인 커스텀 ---
st.set_page_config(page_title="My Quant Model", layout="wide", page_icon="📈")

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        color: black;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] {
            background-color: #262730;
            border: 1px solid #464b5d;
            color: white;
        }
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터 캐싱 ---
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

# --- 3. 사이드바 UI ---
st.sidebar.header("🎛️ 퀀트 모델 설정")

# Step 1
st.sidebar.subheader("Step 1. 종목 선택")
with st.spinner('리스트 로딩 중...'):
    df_stocks = get_stock_list()

default_idx = 0
if '005930' in df_stocks['Code'].values:
    default_idx = df_stocks.index[df_stocks['Code'] == '005930'].tolist()[0]

tab1, tab2 = st.sidebar.tabs(["리스트 검색", "직접 입력"])
with tab1:
    selected_label = st.selectbox("종목을 선택하세요", df_stocks['Label'].values, index=default_idx, label_visibility="collapsed")
    ticker_from_list = selected_label.split('(')[-1].replace(')', '')
with tab2:
    custom_ticker = st.text_input("티커 입력 (예: JEPI)", "", label_visibility="collapsed")

if custom_ticker:
    ticker = custom_ticker.upper()
    display_name = ticker
else:
    ticker = ticker_from_list
    display_name = selected_label.split('(')[0]

# Step 2
st.sidebar.markdown("---")
st.sidebar.subheader("Step 2. 경제지표 믹싱 (100%)")

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

if 'selected_inds' not in st.session_state:
    st.session_state.selected_inds = ["미국 10년물 금리", "원/달러 환율"]

selected_keys = st.sidebar.multiselect(
    "지표 추가/삭제",
    list(indicators_map.keys()),
    default=st.session_state.selected_inds
)

default_weight = 100.0 / len(selected_keys) if selected_keys else 0

table_data = []
for key in selected_keys:
    default_inverse = True if key in ["미국 10년물 금리", "원/달러 환율", "국제유가(WTI)", "미국 기준금리", "VIX (공포지수)"] else False
    table_data.append({
        "Name": key, 
        "Weight": float(f"{default_weight:.1f}"),
        "Inverse": default_inverse
    })

df_config = pd.DataFrame(table_data)

edited_df = st.sidebar.data_editor(
    df_config,
    column_config={
        "Name": st.column_config.TextColumn("지표명", disabled=True),
        "Weight": st.column_config.NumberColumn("비중(%)", min_value=0, max_value=100, step=1, format="%d%%"),
        "Inverse": st.column_config.CheckboxColumn("역방향?")
    },
    hide_index=True,
    use_container_width=True
)

total_sum = edited_df["Weight"].sum()
remaining = 100 - total_sum

if abs(remaining) < 0.1:
    st.sidebar.success(f"✅ 비중 합계: 100%")
    is_valid_total = True
else:
    if remaining > 0:
        st.sidebar.warning(f"⚠️ 합계 부족: {total_sum:.0f}% (+{remaining:.0f}%)")
    else:
        st.sidebar.error(f"🚫 합계 초과: {total_sum:.0f}% ({remaining:.0f}%)")
    is_valid_total = False

configs = {}
for index, row in edited_df.iterrows():
    name = row["Name"]
    configs[name] = {'code': indicators_map[name], 'weight': row["Weight"], 'inverse': row["Inverse"]}

# Step 3
st.sidebar.markdown("---")
st.sidebar.subheader("Step 3. 분석 기간")
period_options = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
selected_period = st.sidebar.select_slider(
    "기간을 선택하세요", 
    options=list(period_options.keys()), 
    value="2년",
    label_visibility="collapsed"
)
start_date = (datetime.now() - timedelta(days=period_options[selected_period])).strftime('%Y-%m-%d')

# --- 4. 데이터 로딩 및 계산 ---
@st.cache_data
def load_data_mix(stock_code, configs, start):
    try:
        stock = fdr.DataReader(stock_code, start)['Close']
    except:
        return None, None, None, None

    macro_score = pd.Series(0, index=stock.index)
    total_weight = 0
    loaded_indicators = {}
    normalized_indicators = {} 

    for name, conf in configs.items():
        try:
            data = fdr.DataReader(conf['code'], start)
            if data.empty: continue
            
            aligned_data = data.iloc[:, 0].reindex(stock.index, method='ffill')
            loaded_indicators[name] = aligned_data

            norm = (aligned_data - aligned_data.min()) / (aligned_data.max() - aligned_data.min())
            if conf['inverse']: norm = 1 - norm
            
            normalized_indicators[name] = norm
            macro_score = macro_score.add(norm * conf['weight'], fill_value=0)
            total_weight += conf['weight']
        except: pass
            
    if total_weight > 0:
        final_macro_index = macro_score / total_weight
    else:
        final_macro_index = pd.Series(0, index=stock.index)

    return stock, final_macro_index, loaded_indicators, normalized_indicators

# --- 5. 메인 화면 ---
st.title(f"📊 {display_name} 퀀트 분석")
st.markdown("주가와 경제 지표(Macro)를 복합적으로 분석하여 **최적의 매매 타이밍**을 찾습니다.")

if not configs:
    st.info("👈 사이드바에서 경제지표를 선택하여 분석을 시작하세요.")
else:
    stock_series, macro_series, raw_indicators, norm_indicators = load_data_mix(ticker, configs, start_date)

    if stock_series is not None and not stock_series.empty:
        df_final = pd.concat([stock_series, macro_series], axis=1).dropna()
        df_final.columns = ['Stock', 'Macro_Index']
        df_final['Stock_Norm'] = (df_final['Stock'] - df_final['Stock'].min()) / (df_final['Stock'].max() - df_final['Stock'].min())
        df_final['Macro_Norm'] = (df_final['Macro_Index'] - df_final['Macro_Index'].min()) / (df_final['Macro_Index'].max() - df_final['Macro_Index'].min())
        
        gap = df_final['Stock_Norm'].iloc[-1] - df_final['Macro_Norm'].iloc[-1]
        last_date = df_final.index[-1].strftime('%Y-%m-%d')
        is_krx = ticker.isdigit()

        # 메트릭 카드
        col1, col2, col3 = st.columns(3)
        with col1:
            if is_krx:
                price_text = f"{df_final['Stock'].iloc[-1]:,.0f}원"
                sub_text = "KRW"
            else:
                ex_rate, _ = get_exchange_rate()
                krw = df_final['Stock'].iloc[-1] * ex_rate
                price_text = f"${df_final['Stock'].iloc[-1]:,.2f}"
                sub_text = f"약 {krw:,.0f}원 (환율 {ex_rate:,.0f}원)"
            st.metric(label=f"주가 ({last_date})", value=price_text, delta=sub_text, delta_color="off")

        with col2:
            st.metric(label="나만의 매크로 점수", value=f"{df_final['Macro_Index'].iloc[-1]:.2f} 점", help="0점(최악) ~ 1점(최상)")

        with col3:
            if gap > 0.3: 
                state_emoji = "🔴 과열"
                delta_color = "inverse"
            elif gap < -0.3: 
                state_emoji = "🔵 저평가"
                delta_color = "normal"
            else: 
                state_emoji = "🟢 적정"
                delta_color = "off"
            st.metric(label="현재 상태 (괴리율)", value=state_emoji, delta=f"Gap: {gap:.2f}", delta_color=delta_color)

        if not is_valid_total:
             st.warning(f"⚠️ 현재 지표 비중 합계가 {total_sum}% 입니다. 정확한 분석을 위해 100%를 맞춰주세요.")

        # --- 차트 영역 ---
        st.subheader("📈 추세 비교 차트")
        # [수정] 볼드(**) 제거된 깔끔한 텍스트
        st.caption("💡 Tip: 차트 하단의 '기간 슬라이더'를 양쪽으로 드래그하면, 원하는 구간만 확대/축소(Zoom)해서 자세히 볼 수 있습니다.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name='주가 (정규화)', line=dict(color='#2962FF', width=2)))
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Macro_Norm'], name='매크로 지수', line=dict(color='#FF4081', width=2, dash='dot')))
        
        fig.update_layout(
            hovermode="x unified",
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        fig.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig, use_container_width=True)

        # 개별 지표 분석
        with st.expander("📊 개별 지표 상세 분석 (클릭해서 열기)", expanded=False):
            st.markdown("##### 내 모델이 주가와 얼마나 비슷하게 움직이는지 확인해보세요.")
            cols = st.columns(2)
            idx = 0
            for name in configs.keys():
                if name in raw_indicators and name in norm_indicators:
                    with cols[idx % 2]:
                        st.markdown(f"**📌 주가 vs {name}**")
                        sub_fig = make_subplots(specs=[[{"secondary_y": True}]])
                        sub_fig.add_trace(
                            go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name="주가", line=dict(color='#bdbdbd', width=1)),
                            secondary_y=False
                        )
                        score_name = "지표(역)" if configs[name]['inverse'] else "지표(정)"
                        sub_fig.add_trace(
                            go.Scatter(x=norm_indicators[name].index, y=norm_indicators[name], name=score_name, line=dict(color='#FF4081', width=2)),
                            secondary_y=True
                        )
                        sub_fig.update_layout(showlegend=False, height=250, margin=dict(l=0, r=0, t=10, b=0))
                        sub_fig.update_yaxes(showticklabels=False)
                        st.plotly_chart(sub_fig, use_container_width=True)
                    idx += 1

        # 용어 설명
        with st.expander("❓ 용어 설명 가이드"):
            st.markdown("""
            * **정규화(Normalization):** 서로 다른 단위의 데이터를 0~1 사이로 변환하여 추세를 비교하는 기술입니다.
            * **괴리율(Gap):** 앙드레 코스톨라니의 '강아지 산책' 이론입니다. 주가(강아지)가 경제(주인)보다 앞서가면(과열) 다시 돌아오고, 뒤쳐지면(저평가) 다시 따라갑니다.
            * **역방향(Inverse):** 환율, 금리처럼 수치가 오를수록 주가에 악영향을 주는 지표는, 점수를 반대로 계산합니다.
            """)

    else:
        st.error("데이터를 불러올 수 없습니다. 종목 코드나 날짜를 확인해주세요.")
