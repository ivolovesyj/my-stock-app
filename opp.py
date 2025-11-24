import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

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
    "달러 인덱스": "FRED:DTWEXBGS", "VIX (공포지수)": "FRED:VIXCLS",
    "M2 통화량": "FRED:M2SL", "미국 실업률": "FRED:UNRATE"
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

# --- [UPGRADE] 시차 적용 알고리즘 ---
def find_optimal_mix(stock_code, start_date, lag_days=0, progress_bar=None, status_text=None):
    if status_text: status_text.text("🔍 1/4단계: 주가 데이터 수집 및 시차 적용...")
    if progress_bar: progress_bar.progress(10)
    time.sleep(0.1)

    try:
        stock = fdr.DataReader(stock_code, start_date)['Close'].dropna()
        if stock.empty: return None
    except: return None

    # [핵심] 주가 데이터를 미래로 당겨오거나(Shift -), 지표를 과거로 미룸.
    # 여기서는 '지표(오늘)' vs '주가(미래)'를 비교하기 위해 주가를 -lag_days 만큼 shift 합니다.
    # 예: lag=20이면, 오늘의 지표값과 20일 뒤의 주가값을 같은 행에 둡니다.
    target_stock = stock.shift(-lag_days).dropna()
    
    # 비교를 위해 인덱스 교집합(common index)만 남김
    common_index = target_stock.index
    target_stock_norm = (target_stock - target_stock.min()) / (target_stock.max() - target_stock.min())

    if status_text: status_text.text(f"📊 2/4단계: {lag_days}일 선행 지표 스캔 중...")
    if progress_bar: progress_bar.progress(30)
    
    results = []
    count = 0
    for name, code in INDICATORS_MAP.items():
        count += 1
        if progress_bar: progress_bar.progress(30 + int(count/len(INDICATORS_MAP)*40))
        try:
            indi = fdr.DataReader(code, start_date)
            if indi.empty: continue
            
            # 주가 인덱스에 맞춰 지표 정렬 (보간법 사용)
            aligned_indi = indi.iloc[:, 0].reindex(stock.index).interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
            
            # 시차 적용된 주가 인덱스와 맞춤
            aligned_indi = aligned_indi.loc[common_index]
            
            if aligned_indi.empty: continue

            indi_norm = (aligned_indi - aligned_indi.min()) / (aligned_indi.max() - aligned_indi.min())
            
            # 상관계수 계산
            corr = target_stock_norm.corr(indi_norm)
            if pd.isna(corr): continue
            
            results.append({'name': name, 'corr': corr, 'abs_corr': abs(corr)})
        except: continue
    
    if not results: return None

    if status_text: status_text.text("🧠 3/4단계: 최적 비중 계산...")
    if progress_bar: progress_bar.progress(80)
    
    df_res = pd.DataFrame(results)
    # 상관계수 0.3 이상만 필터링
    df_res = df_res[df_res['abs_corr'] >= 0.3].sort_values('abs_corr', ascending=False).head(3)
    
    if df_res.empty: return "NO_CORRELATION"

    total_corr = df_res['abs_corr'].sum()
    optimized = []
    for _, row in df_res.iterrows():
        optimized.append({
            "Name": row['name'],
            "Weight": float(f"{(row['abs_corr']/total_corr)*100:.1f}"),
            "Inverse": True if row['corr'] < 0 else False
        })
        
    if status_text: status_text.text("✅ 완료!")
    if progress_bar: progress_bar.progress(100)
    time.sleep(0.5)
    return optimized

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

# [NEW] 시차(Lag) 설정
lag_days = st.sidebar.slider("⏳ 지표 선행 기간 (일)", 0, 60, 0, help="지표가 주가보다 며칠 먼저 움직이는지 분석합니다. (예: 20일 설정 시, 20일 전 지표와 오늘 주가 비교)")

# 분석 기간
period_opt = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
sel_period = st.sidebar.select_slider("분석 기간", list(period_opt.keys()), value="2년")
days = period_opt[sel_period]
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# AI 최적화 버튼
if st.sidebar.button("⚡ AI 최적 조합 찾기 (Auto-Fit)", type="primary", use_container_width=True):
    stat = st.sidebar.empty()
    prog = st.sidebar.progress(0)
    # lag_days를 넘겨줍니다
    res = find_optimal_mix(ticker, start_date, lag_days, prog, stat)
    stat.empty(); prog.empty()
    
    if res == "NO_CORRELATION": st.sidebar.warning("유의미한 지표 없음 (독자적 움직임)")
    elif res:
        st.session_state.opt_data = res
        st.sidebar.success(f"최적 조합 {len(res)}개 발견! (시차 {lag_days}일 적용)")
        st.rerun()
    else: st.sidebar.error("오류 발생")

if 'opt_data' in st.session_state: cur_data = st.session_state.opt_data
else: cur_data = [{"Name": "미국 10년물 금리", "Weight": 50.0, "Inverse": True}, {"Name": "원/달러 환율", "Weight": 50.0, "Inverse": True}]

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

configs = {r["Name"]: {'code': INDICATORS_MAP[r["Name"]], 'weight': r["Weight"], 'inverse': r["Inverse"]} for _, r in ed_df.iterrows() if r["Name"]}

# --- 4. 메인 로직 (시차 적용 데이터 로딩) ---
@st.cache_data
def load_data_mix(stock_code, configs, start, lag=0):
    try: stock = fdr.DataReader(stock_code, start)['Close'].interpolate()
    except: return None, None, None, None
    
    # 주가는 그대로 두고 (현재 기준), 지표 점수 계산 시 과거 데이터를 가져오는 방식이 아니라
    # 시각화를 위해 '지표 데이터를 미래로 미는(Shift)' 방식을 씁니다.
    # 그래야 차트에서 "20일 전 지표"가 "오늘 주가"와 같은 x축에 찍힙니다.
    
    macro = pd.Series(0, index=stock.index)
    raws = {}; norms = {}
    total_w = 0
    
    for name, conf in configs.items():
        try:
            d = fdr.DataReader(conf['code'], start)
            if d.empty: continue
            
            # 원본 데이터 정렬
            aligned = d.iloc[:,0].reindex(stock.index).interpolate().fillna(method='bfill').fillna(method='ffill')
            raws[name] = aligned
            
            # [UPGRADE] 시차 적용 (지표를 미래로 밈 -> 선행지표 확인용)
            # lag가 20이면, 오늘의 주가 위치에 20일 전 지표값이 옴.
            shifted_aligned = aligned.shift(lag) 
            
            # 정규화 (Shift된 데이터 기준)
            nm = (shifted_aligned - shifted_aligned.min()) / (shifted_aligned.max() - shifted_aligned.min())
            if conf['inverse']: nm = 1 - nm
            
            norms[name] = nm
            macro = macro.add(nm * conf['weight'], fill_value=0)
            total_w += conf['weight']
        except: pass
        
    final_macro = macro / total_w if total_w > 0 else pd.Series(0, index=stock.index)
    return stock, final_macro, raws, norms

# --- 5. 화면 출력 ---
st.title(f"📊 {display_name} 퀀트 분석")

if not configs: st.info("사이드바 설정을 확인하세요.")
else:
    # lag_days 전달
    stock, macro, raws, norms = load_data_mix(ticker, configs, start_date, lag_days)
    
    if stock is not None:
        # 데이터 병합 (NaN 제거 - 시차 때문에 앞부분이 비게 됨)
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
                rate, _ = get_exchange_rate()
                val = f"${df['Stock'].iloc[-1]:,.2f}"
                sub = f"약 {df['Stock'].iloc[-1]*rate:,.0f}원"
            st.metric(f"주가 ({last_dt})", val, sub, delta_color="off")
            
        with c2: 
            # 시차 표시 추가
            lag_info = f"(시차 {lag_days}일 적용)" if lag_days > 0 else "(동행)"
            st.metric(f"내 매크로 점수 {lag_info}", f"{df['Macro'].iloc[-1]:.2f} 점", "0~1 Scale")
        
        with c3:
            if gap > 0.3: st.metric("괴리율 상태", "🔴 과열", f"Gap {gap:.2f}", delta_color="inverse")
            elif gap < -0.3: st.metric("괴리율 상태", "🔵 저평가", f"Gap {gap:.2f}", delta_color="normal")
            else: st.metric("괴리율 상태", "🟢 적정", f"Gap {gap:.2f}", delta_color="off")

        # 차트
        st.subheader("📈 추세 비교")
        
        # 안내 문구 강화
        if lag_days > 0:
            st.info(f"ℹ️ 현재 **{lag_days}일 선행 분석** 모드입니다. 차트의 빨간 점선은 **{lag_days}일 전의 경제지표**를 오늘 날짜로 당겨서 보여줍니다. (즉, 빨간 선이 파란 선보다 먼저 움직이는지 확인하세요!)")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Stock_N'], name='주가(정규화)', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.index, y=df['Macro_N'], name=f'매크로 모델 (Lag {lag_days})', line=dict(color='red', dash='dot')))
        fig.update_xaxes(rangeslider_visible=True)
        fig.update_layout(hovermode="x unified", height=400, margin=dict(t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # 예측력 검증
        st.markdown("---")
        st.subheader("🔮 이 모델의 예측력 검증")
        
        analysis_df = pd.DataFrame({
            'Gap': df['Stock_N'] - df['Macro_N'],
            'Next_Return': df['Stock'].pct_change(periods=20).shift(-20) * 100 
        }).dropna()

        if not analysis_df.empty:
            corr_predict = analysis_df['Gap'].corr(analysis_df['Next_Return'])
            if corr_predict < 0: score = int(abs(corr_predict) * 100)
            else: score = 0

            c_res1, c_res2 = st.columns([1, 2])
            with c_res1:
                st.markdown("#### 🤖 AI 신뢰도 점수")
                if score >= 60:
                    msg = "✅ **매우 높음**\n\n선행성이 확인되었습니다!"
                elif score >= 30:
                    msg = "⚠️ **보통**\n\n참고용으로만 보세요."
                else:
                    msg = "❌ **낮음**\n\n예측력이 없습니다."
                st.metric("점수", f"{score}점")
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

        # 주의사항 (아이스크림 오류)
        with st.expander("⚠️ 분석 시 주의사항 (필독!)"):
            st.markdown("""
            1.  **아이스크림과 상어 오류:** 상관관계가 높다고 해서 반드시 인과관계가 있는 것은 아닙니다. (우연의 일치일 수 있음)
            2.  **후행성:** 이 알고리즘은 '과거 데이터'에 최적화되어 있습니다. 시장의 판도가 바뀌면(예: 금리 장세 -> 실적 장세) 예측력이 떨어질 수 있습니다.
            3.  **Lag(시차):** '지표 선행 기간'을 조절해보며, 빨간 점선이 파란 실선보다 먼저 꺾이는지 확인하는 것이 진짜 고수의 분석법입니다.
            """)

    else: st.error("데이터 없음")
