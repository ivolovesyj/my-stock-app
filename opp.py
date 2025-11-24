import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import statsmodels.api as sm

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="My Quant Model (Pro)", layout="wide", page_icon="📈")

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] {
            background-color: #262730;
            border: 1px solid #464b5d;
            color: white;
        }
    }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. 데이터 캐싱 ---
INDICATORS_MAP = {
    "미국 10년물 금리": "FRED:DGS10", "원/달러 환율": "FRED:DEXKOUS",
    "국제유가(WTI)": "FRED:DCOILWTICO", "나스닥 지수": "FRED:NASDAQCOM",
    "S&P 500 지수": "FRED:SP500", "미국 기준금리": "FRED:FEDFUNDS",
    "달러 인덱스": "FRED:DTWEXBGS", "VIX (공포지수)": "FRED:VIXCLS"
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
    except: df_total = df_base
    df_total['Label'] = df_total['Name'] + " (" + df_total['Code'] + ")"
    return df_total

@st.cache_data
def get_exchange_rate():
    try:
        df = fdr.DataReader('USD/KRW', (datetime.now() - timedelta(days=7)))
        return df['Close'].iloc[-1], df.index[-1].strftime('%Y-%m-%d')
    except: return 1400.0, datetime.now().strftime('%Y-%m-%d')

# --- 알고리즘 함수 ---
def find_optimal_mix(stock_code, start_date, lag_days=0, progress_bar=None, status_text=None):
    if status_text: status_text.text("🔍 1/4단계: 데이터 수집 중...")
    if progress_bar: progress_bar.progress(10)
    time.sleep(0.1)

    try:
        stock = fdr.DataReader(stock_code, start_date)['Close'].dropna()
        if stock.empty: return None
    except: return None

    # 시차 적용
    target_stock = stock.shift(-lag_days).dropna()
    common_index = target_stock.index
    y = (target_stock - target_stock.min()) / (target_stock.max() - target_stock.min())

    if status_text: status_text.text(f"📊 2/4단계: 경제지표 전처리 (시차 {lag_days}일)...")
    if progress_bar: progress_bar.progress(30)
    
    indicator_data = {}
    count = 0
    for name, code in INDICATORS_MAP.items():
        count += 1
        if progress_bar: progress_bar.progress(30 + int(count/len(INDICATORS_MAP)*20))
        try:
            indi = fdr.DataReader(code, start_date)
            if indi.empty: continue
            aligned = indi.iloc[:, 0].reindex(stock.index).interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
            aligned = aligned.loc[common_index]
            norm = (aligned - aligned.min()) / (aligned.max() - aligned.min())
            indicator_data[name] = norm
        except: continue
    
    if not indicator_data: return None
    X = pd.DataFrame(indicator_data)

    if status_text: status_text.text("🧠 3/4단계: 다중회귀분석(OLS) 수행 중...")
    if progress_bar: progress_bar.progress(60)
    
    X_aug = sm.add_constant(X)
    
    try:
        model = sm.OLS(y, X_aug).fit()
        params = model.params.drop('const')
        abs_params = params.abs().sort_values(ascending=False)
        top_3_names = abs_params.head(3).index.tolist()
        r_squared = model.rsquared
    except: return "ERROR"

    if not top_3_names: return "NO_CORRELATION"

    if status_text: status_text.text(f"✅ 4/4단계: 완료 (설명력 {r_squared*100:.1f}%)")
    if progress_bar: progress_bar.progress(100)
    time.sleep(0.5)

    final_config = []
    for name in top_3_names:
        coef = params[name]
        is_inverse = True if coef < 0 else False
        weight = (abs(coef) / abs_params[top_3_names].sum()) * 100
        final_config.append({
            "Name": name,
            "Weight": float(f"{weight:.1f}"),
            "Inverse": is_inverse
        })
        
    return final_config, r_squared

# --- 3. 사이드바 ---
st.sidebar.header("🎛️ 퀀트 모델 설정")
st.sidebar.subheader("Step 1. 종목 선택")
with st.spinner('로딩 중...'): df_stocks = get_stock_list()

default_idx = 0
if '005930' in df_stocks['Code'].values:
    default_idx = df_stocks.index[df_stocks['Code'] == '005930'].tolist()[0]

tab1, tab2 = st.sidebar.tabs(["리스트", "직접입력"])
with tab1:
    sel_label = st.selectbox("종목", df_stocks['Label'].values, index=default_idx, label_visibility="collapsed")
    ticker_list = sel_label.split('(')[-1].replace(')', '')
with tab2:
    custom_tk = st.text_input("티커", "", placeholder="TSLA", label_visibility="collapsed")

ticker = custom_tk.upper() if custom_tk else ticker_list
display_name = ticker if custom_tk else sel_label.split('(')[0]

st.sidebar.markdown("---")
st.sidebar.subheader("Step 2. 지표 분석 설정")

lag_days = st.sidebar.slider("⏳ 지표 선행 기간 (일)", 0, 60, 0)
period_opt = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
sel_period = st.sidebar.select_slider("분석 기간", list(period_opt.keys()), value="2년")
days = period_opt[sel_period]
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

if st.sidebar.button("⚡ AI 최적 조합 찾기 (Auto-Fit)", type="primary", use_container_width=True):
    stat = st.sidebar.empty()
    prog = st.sidebar.progress(0)
    result = find_optimal_mix(ticker, start_date, lag_days, prog, stat)
    stat.empty(); prog.empty()
    
    if isinstance(result, tuple):
        res_data, r2_score = result
        st.session_state.opt_data = res_data
        st.session_state.r2_score = r2_score
        st.sidebar.success(f"✅ 모델 생성 완료! (설명력: {r2_score*100:.1f}%)")
        st.rerun()
    elif result == "NO_CORRELATION": st.sidebar.warning("유의미한 지표 없음")
    else: st.sidebar.error("분석 중 오류 발생")

if 'opt_data' in st.session_state: cur_data = st.session_state.opt_data
else: cur_data = [{"Name": "미국 10년물 금리", "Weight": 50.0, "Inverse": True}, {"Name": "원/달러 환율", "Weight": 50.0, "Inverse": True}]

if 'r2_score' in st.session_state:
    r2 = st.session_state.r2_score * 100
    if r2 > 70: color = "green"
    elif r2 > 40: color = "orange"
    else: color = "red"
    st.sidebar.markdown(f"📊 **현재 모델의 설명력($R^2$):** :{color}[**{r2:.1f}%**]")

st.sidebar.caption("👇 지표 구성 수정")
ed_df = st.sidebar.data_editor(pd.DataFrame(cur_data), column_config={
    "Name": st.column_config.SelectboxColumn("지표", options=list(INDICATORS_MAP.keys()), required=True),
    "Weight": st.column_config.NumberColumn("비중", min_value=0, max_value=100, step=0.1, format="%.1f"),
    "Inverse": st.column_config.CheckboxColumn("역방향?")
}, num_rows="dynamic", hide_index=True, use_container_width=True)

tot_sum = ed_df["Weight"].sum()
rem = 100 - tot_sum
if abs(rem) < 0.1: st.sidebar.success("✅ 비중 합계 100%")
else: st.sidebar.warning(f"⚠️ 합계 {tot_sum:.1f}%")

configs = {
    r["Name"]: {'code': INDICATORS_MAP[r["Name"]], 'weight': r["Weight"], 'inverse': r["Inverse"]} 
    for _, r in ed_df.iterrows() 
    if r["Name"] and r["Name"] in INDICATORS_MAP
}

# --- 4. 메인 로직 ---
@st.cache_data
def load_data_mix(stock_code, configs, start, lag=0):
    try: stock = fdr.DataReader(stock_code, start)['Close'].interpolate()
    except: return None, None, None, None
    
    macro = pd.Series(0, index=stock.index)
    raws = {}; norms = {}
    total_w = 0
    
    for name, conf in configs.items():
        try:
            d = fdr.DataReader(conf['code'], start)
            if d.empty: continue
            align = d.iloc[:,0].reindex(stock.index).interpolate().fillna(method='bfill').fillna(method='ffill')
            raws[name] = align
            shifted_align = align.shift(lag) 
            
            # [수정] 앞뒤가 잘릴 수 있으므로 정규화 안전장치
            if shifted_align.dropna().empty: continue
            
            nm = (shifted_align - shifted_align.min()) / (shifted_align.max() - shifted_align.min())

            if conf['inverse']: nm = 1 - nm
            norms[name] = nm
            
            # fill_value=0 대신 NaN 유지하여 나중에 dropna로 처리
            macro = macro.add(nm * conf['weight'], fill_value=0) 
            total_w += conf['weight']
        except: pass
        
    if total_weight > 0:
        final_macro = macro / total_w
        # [FIX] 시차(Lag)로 인한 결측치 제거 (0으로 떨어지는 문제 해결)
        if lag > 0: final_macro.iloc[:lag] = np.nan
        elif lag < 0: final_macro.iloc[lag:] = np.nan
    else:
        final_macro = pd.Series(0, index=stock.index)

    return stock, final_macro, raws, norms

# --- 5. 화면 출력 ---
st.title(f"📊 {display_name} 퀀트 분석")

if not configs: st.info("사이드바 설정을 확인하세요.")
else:
    stock, macro, raws, norms = load_data_mix(ticker, configs, start_date, lag_days)
    
    if stock is not None:
        df = pd.concat([stock, macro], axis=1).dropna()
        df.columns = ['Stock', 'Macro']
        
        df['Stock_N'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
        df['Macro_N'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
        gap = df['Stock_N'].iloc[-1] - df['Macro_N'].iloc[-1]
        
        c1, c2, c3 = st.columns(3)
        last_dt = df.index[-1].strftime('%Y-%m-%d')
        is_krx = ticker.isdigit()
        
        with c1:
            if is_krx: val = f"{df['Stock'].iloc[-1]:,.0f}원"; sub = "KRW"
            else: 
                rate = get_exchange_rate()
                val = f"${df['Stock'].iloc[-1]:,.2f}"
                sub = f"약 {df['Stock'].iloc[-1]*rate:,.0f}원"
            st.metric(f"주가 ({last_dt})", val, sub, delta_color="off")
            
        with c2: 
            lag_info = f"(시차 {lag_days}일)" if lag_days > 0 else "(동행)"
            st.metric(f"매크로 모델 점수 {lag_info}", f"{df['Macro'].iloc[-1]:.2f} 점", "0~1 Scale")
        
        with c3:
            if gap > 0.3: st.metric("상태", "🔴 과열", f"Gap {gap:.2f}", delta_color="inverse")
            elif gap < -0.3: st.metric("상태", "🔵 저평가", f"Gap {gap:.2f}", delta_color="normal")
            else: st.metric("상태", "🟢 적정", f"Gap {gap:.2f}", delta_color="off")

        st.subheader("📈 추세 비교")
        if lag_days > 0:
            st.info(f"ℹ️ 현재 **{lag_days}일 선행 분석** 중입니다. 빨간 선(경제지표)이 파란 선(주가)보다 먼저 움직이는지 확인하세요.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Stock_N'], name='주가(정규화)', line=dict(color='#2962FF', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['Macro_N'], name=f'매크로 모델', line=dict(color='#FF4081', width=2, dash='dot')))
        fig.update_xaxes(rangeslider_visible=True)
        fig.update_layout(hovermode="x unified", height=400, margin=dict(t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("🔮 예측력 검증 (Backtest)")
        
        analysis_df = pd.DataFrame({
            'Gap': df['Stock_N'] - df['Macro_N'],
            'Next_Return': df['Stock'].pct_change(periods=20).shift(-20) * 100 
        }).dropna()

        if not analysis_df.empty:
            corr_predict = analysis_df['Gap'].corr(analysis_df['Next_Return'])
            score = int(abs(corr_predict) * 100) if corr_predict < 0 else 0

            c_res1, c_res2 = st.columns([1, 2])
            with c_res1:
                st.markdown("#### 🤖 AI 신뢰도 점수")
                if score >= 60: msg = "✅ **매우 높음**\n\n신뢰할 수 있는 모델입니다."
                elif score >= 30: msg = "⚠️ **보통**\n\n참고용으로 적합합니다."
                else: msg = "❌ **낮음**\n\n예측력이 약합니다."
                
                st.metric("점수 (100점 만점)", f"{score}점")
                st.progress(score)
                st.info(msg)

            with c_res2:
                try:
                    fig_scat = px.scatter(
                        analysis_df, x='Gap', y='Next_Return', 
                        trendline="ols", trendline_color_override="red",
                        title="괴리율(X) vs 미래수익률(Y)", opacity=0.3
                    )
                except:
                    fig_scat = px.scatter(analysis_df, x='Gap', y='Next_Return', title="괴리율 vs 수익률", opacity=0.3)
                fig_scat.update_layout(height=350)
                st.plotly_chart(fig_scat, use_container_width=True)

        with st.expander("📊 개별 지표 상세 보기"):
            cols = st.columns(2)
            for i, name in enumerate(configs.keys()):
                if name in norms:
                    with cols[i%2]:
                        fig_sub = make_subplots(specs=[[{"secondary_y": True}]])
                        fig_sub.add_trace(go.Scatter(x=df.index, y=df['Stock_N'], name="주가", line=dict(color='#ccc')), secondary_y=False)
                        fname = f"{name} (역)" if configs[name]['inverse'] else name
                        fig_sub.add_trace(go.Scatter(x=norms[name].index, y=norms[name], name=fname, line=dict(color='blue')), secondary_y=True)
                        fig_sub.update_layout(title=name, height=250, showlegend=False, margin=dict(t=30,b=0))
                        fig_sub.update_yaxes(showticklabels=False)
                        st.plotly_chart(fig_sub, use_container_width=True)

    else: st.error("데이터 없음")
