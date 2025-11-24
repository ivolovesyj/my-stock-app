import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time  # [NEW] 연출을 위해 time 모듈 추가

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
INDICATORS_MAP = {
    "미국 10년물 금리": "FRED:DGS10", 
    "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO", 
    "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500", 
    "미국 기준금리": "FRED:FEDFUNDS",
    "달러 인덱스": "FRED:DTWEXBGS",
    "VIX (공포지수)": "FRED:VIXCLS"
}

@st.cache_data
def get_stock_list():
    base_data = [
        {'Code': '005930', 'Name': '삼성전자'}, {'Code': '000660', 'Name': 'SK하이닉스'},
        {'Code': '005380', 'Name': '현대차'}, {'Code': '035420', 'Name': 'NAVER'},
        {'Code': '035720', 'Name': '카카오'}, {'Code': 'AAPL', 'Name': '애플 (Apple)'},
        {'Code': 'NVDA', 'Name': '엔비디아 (NVIDIA)'}, {'Code': 'TSLA', 'Name': '테슬라 (Tesla)'},
        {'Code': 'MSFT', 'Name': '마이크로소프트'}, {'Code': 'GOOGL', 'Name': '구글'},
        {'Code': 'AMZN', 'Name': '아마존'}, {'Code': 'DIS', 'Name': '월트 디즈니'},
        {'Code': 'KO', 'Name': '코카콜라'}, {'Code': 'SBUX', 'Name': '스타벅스'},
        {'Code': 'O', 'Name': '리얼티인컴'}, {'Code': 'QQQ', 'Name': '나스닥 100 (QQQ)'},
        {'Code': 'SPY', 'Name': 'S&P 500 (SPY)'}, {'Code': 'SCHD', 'Name': '슈왑 배당 (SCHD)'},
        {'Code': 'JEPI', 'Name': 'JP모건 커버드콜'}, {'Code': 'PLTR', 'Name': '팔란티어'},
        {'Code': 'IONQ', 'Name': '아이온큐'}
    ]
    df_base = pd.DataFrame(base_data)
    
    try:
        df_krx = fdr.StockListing('KRX')[['Code', 'Name']]
        df_total = pd.concat([df_base, df_krx]).drop_duplicates(subset=['Code'])
    except:
        df_total = df_base

    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

@st.cache_data
def get_exchange_rate():
    try:
        df = fdr.DataReader('USD/KRW', (datetime.now() - timedelta(days=7)))
        return df['Close'].iloc[-1], df.index[-1].strftime('%Y-%m-%d')
    except:
        return 1400.0, datetime.now().strftime('%Y-%m-%d')

# --- [수정] 최적화 알고리즘 함수 (캐싱 제거 - UI 연출을 위해) ---
# (st.cache_data를 쓰면 연출이 스킵되므로, 연출을 보고 싶다면 제거하거나 유지하고 연출을 분리해야 함.
# 여기서는 '실시간 연출'을 위해 캐싱을 잠시 뺍니다. 속도 차이가 크지 않다면 이게 UX에 좋습니다.)
def find_optimal_mix(stock_code, start_date, progress_bar=None, status_text=None):
    
    # 1. 주가 데이터 수집
    if status_text: status_text.text("🔍 1/4단계: 주가 데이터 수집 중...")
    if progress_bar: progress_bar.progress(10)
    time.sleep(0.3) # 연출용 대기

    try:
        stock = fdr.DataReader(stock_code, start_date)['Close']
        stock = stock.dropna()
        if stock.empty: return None
    except:
        return None

    stock_norm = (stock - stock.min()) / (stock.max() - stock.min())

    # 2. 경제지표 스캔
    if status_text: status_text.text("📊 2/4단계: 글로벌 경제지표 스캔 및 상관관계 분석...")
    if progress_bar: progress_bar.progress(30)
    
    results = []
    total_indicators = len(INDICATORS_MAP)
    current_count = 0

    for name, code in INDICATORS_MAP.items():
        # 진행률 업데이트 (연출)
        current_count += 1
        if progress_bar: 
            progress = 30 + int((current_count / total_indicators) * 40) # 30% ~ 70% 구간
            progress_bar.progress(progress)
        
        try:
            indi = fdr.DataReader(code, start_date)
            if indi.empty: continue
            
            aligned_indi = indi.iloc[:, 0].reindex(stock.index).interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
            indi_norm = (aligned_indi - aligned_indi.min()) / (aligned_indi.max() - aligned_indi.min())
            corr = stock_norm.corr(indi_norm)
            
            if pd.isna(corr): continue
            results.append({'name': name, 'corr': corr, 'abs_corr': abs(corr)})
        except:
            continue
    
    if not results: return None

    # 3. 최적화 로직
    if status_text: status_text.text("🧠 3/4단계: AI 최적 비중 계산 중...")
    if progress_bar: progress_bar.progress(80)
    time.sleep(0.5) # 연출용 대기

    df_res = pd.DataFrame(results)
    df_res = df_res[df_res['abs_corr'] >= 0.3] # 필터링
    
    if df_res.empty: return "NO_CORRELATION"

    df_res = df_res.sort_values('abs_corr', ascending=False).head(3)

    total_corr = df_res['abs_corr'].sum()
    
    optimized_config = []
    for _, row in df_res.iterrows():
        weight = (row['abs_corr'] / total_corr) * 100
        is_inverse = True if row['corr'] < 0 else False 
        optimized_config.append({
            "Name": row['name'],
            "Weight": float(f"{weight:.1f}"),
            "Inverse": is_inverse
        })
        
    # 4. 완료
    if status_text: status_text.text("✅ 4/4단계: 완료!")
    if progress_bar: progress_bar.progress(100)
    time.sleep(0.3)
        
    return optimized_config

# --- 3. 사이드바 UI ---
st.sidebar.header("🎛️ 퀀트 모델 설정")

# Step 1. 종목 선택
st.sidebar.subheader("Step 1. 종목 선택")
with st.spinner('리스트 로딩 중...'):
    df_stocks = get_stock_list()

default_idx = 0
if '005930' in df_stocks['Code'].values:
    default_idx = df_stocks.index[df_stocks['Code'] == '005930'].tolist()[0]

tab1, tab2 = st.sidebar.tabs(["리스트 검색", "직접 입력"])
with tab1:
    selected_label = st.selectbox("종목 선택", df_stocks['Label'].values, index=default_idx, label_visibility="collapsed")
    ticker_from_list = selected_label.split('(')[-1].replace(')', '')
with tab2:
    custom_ticker = st.text_input("티커 입력", "", placeholder="예: TSLA", label_visibility="collapsed")

if custom_ticker:
    ticker = custom_ticker.upper()
    display_name = ticker
else:
    ticker = ticker_from_list
    display_name = selected_label.split('(')[0]

# Step 2. 지표 믹싱
st.sidebar.markdown("---")
st.sidebar.subheader("Step 2. 경제지표 믹싱")

# 기간 설정
period_options = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
selected_period = st.sidebar.select_slider("분석 기간", options=list(period_options.keys()), value="2년")
days = period_options[selected_period]
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# [NEW] AI 최적화 버튼 (연출 추가)
if st.sidebar.button("⚡ AI 최적 조합 찾기 (Auto-Fit)", type="primary", use_container_width=True):
    # 사이드바에 빈 공간(placeholder)을 만들어서 진행상황 표시
    status_text = st.sidebar.empty()
    progress_bar = st.sidebar.progress(0)
    
    # 함수 실행 시 progress_bar와 status_text를 넘겨줌
    opt_result = find_optimal_mix(ticker, start_date, progress_bar, status_text)
    
    # 완료 후 정리
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    if opt_result == "NO_CORRELATION":
        st.sidebar.warning("⚠️ 유의미한 상관관계를 가진 지표를 찾지 못했습니다.")
    elif opt_result:
        st.session_state.optimized_data = opt_result
        st.sidebar.success(f"✅ 최적 조합 발견! ({len(opt_result)}개 지표)")
        st.rerun() # 화면 갱신
    else:
        st.sidebar.error("데이터 분석 중 오류가 발생했습니다.")

# 데이터 에디터 초기값
if 'optimized_data' in st.session_state:
    current_data = st.session_state.optimized_data
else:
    current_data = [
        {"Name": "미국 10년물 금리", "Weight": 50.0, "Inverse": True},
        {"Name": "원/달러 환율", "Weight": 50.0, "Inverse": True}
    ]

df_config = pd.DataFrame(current_data)

st.sidebar.caption("👇 지표 구성 및 비중(%) 수정")
edited_df = st.sidebar.data_editor(
    df_config,
    column_config={
        "Name": st.column_config.SelectboxColumn("지표명", options=list(INDICATORS_MAP.keys()), required=True),
        "Weight": st.column_config.NumberColumn("비중(%)", min_value=0, max_value=100, step=0.1, format="%.1f"),
        "Inverse": st.column_config.CheckboxColumn("역방향?")
    },
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    key="editor"
)

# 합계 검증
total_sum = edited_df["Weight"].sum()
remaining = 100 - total_sum

if abs(remaining) < 0.1:
    st.sidebar.success(f"✅ 비중 합계: 100%")
    is_valid_total = True
else:
    if remaining > 0:
        st.sidebar.warning(f"⚠️ 합계 부족: {total_sum:.1f}% (+{remaining:.1f}%)")
    else:
        st.sidebar.error(f"🚫 합계 초과: {total_sum:.1f}% ({remaining:.1f}%)")
    is_valid_total = False

# 설정값 변환
configs = {}
for index, row in edited_df.iterrows():
    if row["Name"]:
        configs[row["Name"]] = {'code': INDICATORS_MAP[row["Name"]], 'weight': row["Weight"], 'inverse': row["Inverse"]}

# --- 4. 메인 로직 (믹싱 계산) ---
@st.cache_data
def load_data_mix(stock_code, configs, start):
    try:
        stock = fdr.DataReader(stock_code, start)['Close']
        stock = stock.interpolate(method='linear')
    except: return None, None, None, None

    macro_score = pd.Series(0, index=stock.index)
    total_weight = 0
    loaded_indicators = {}
    normalized_indicators = {} 

    for name, conf in configs.items():
        try:
            data = fdr.DataReader(conf['code'], start)
            if data.empty: continue
            aligned = data.iloc[:, 0].reindex(stock.index).interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
            loaded_indicators[name] = aligned
            
            norm = (aligned - aligned.min()) / (aligned.max() - aligned.min())
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

# --- 5. UI 출력 ---
st.title(f"📊 {display_name} 퀀트 분석")
st.markdown("주가와 경제 지표(Macro)를 복합적으로 분석하여 **최적의 매매 타이밍**을 찾습니다.")

if not configs:
    st.info("👈 사이드바에서 경제지표를 선택하거나 'AI 최적 조합 찾기'를 눌러보세요.")
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

        col1, col2, col3 = st.columns(3)
        with col1:
            if is_krx:
                price_text = f"{df_final['Stock'].iloc[-1]:,.0f}원"
                sub_text = "KRW"
            else:
                ex_rate = get_exchange_rate()
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
             st.warning(f"⚠️ 현재 지표 비중 합계가 {total_sum:.1f}% 입니다. 100%를 맞춰주세요.")

        # 차트
        st.subheader("📈 추세 비교 차트")
        st.caption("💡 Tip: 차트 하단의 '기간 슬라이더'를 양쪽으로 드래그하면, 원하는 구간만 확대/축소(Zoom)해서 자세히 볼 수 있습니다.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name='주가 (정규화)', line=dict(color='#2962FF', width=2)))
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Macro_Norm'], name='매크로 지수', line=dict(color='#FF4081', width=2, dash='dot')))
        
        fig.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.02, x=1), height=400)
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
                        sub_fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name="주가", line=dict(color='#bdbdbd', width=1)), secondary_y=False)
                        score_name = "지표(역)" if configs[name]['inverse'] else "지표(정)"
                        sub_fig.add_trace(go.Scatter(x=norm_indicators[name].index, y=norm_indicators[name], name=score_name, line=dict(color='#FF4081', width=2)), secondary_y=True)
                        sub_fig.update_layout(showlegend=False, height=250, margin=dict(l=0, r=0, t=10, b=0))
                        sub_fig.update_yaxes(showticklabels=False)
                        st.plotly_chart(sub_fig, use_container_width=True)
                    idx += 1

        with st.expander("❓ 용어 설명 가이드"):
            st.markdown("""
            * **정규화(Normalization):** 서로 다른 단위의 데이터를 0~1 사이로 변환하여 추세를 비교하는 기술입니다.
            * **괴리율(Gap):** 앙드레 코스톨라니의 '강아지 산책' 이론입니다. 주가(강아지)가 경제(주인)보다 앞서가면(과열) 다시 돌아오고, 뒤쳐지면(저평가) 다시 따라갑니다.
            * **역방향(Inverse):** 환율, 금리처럼 수치가 오를수록 주가에 악영향을 주는 지표는, 점수를 반대로 계산합니다.
            """)

    else:
        st.error("데이터를 불러올 수 없습니다. 종목 코드나 날짜를 확인해주세요.")
