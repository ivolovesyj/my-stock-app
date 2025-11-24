import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots  # [복구됨] 이 친구가 빠져서 에러가 났었습니다!
from datetime import datetime, timedelta
import time

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="My Quant Model", layout="wide", page_icon="📈")

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
def find_optimal_mix(stock_code, start_date, progress_bar=None, status_text=None):
    if status_text: status_text.text("🔍 1/4단계: 데이터 수집 중...")
    if progress_bar: progress_bar.progress(10)
    time.sleep(0.1)

    try:
        stock = fdr.DataReader(stock_code, start_date)['Close'].dropna()
        if stock.empty: return None
    except: return None

    stock_norm = (stock - stock.min()) / (stock.max() - stock.min())

    if status_text: status_text.text("📊 2/4단계: 상관관계 분석 중...")
    if progress_bar: progress_bar.progress(30)
    
    results = []
    count = 0
    for name, code in INDICATORS_MAP.items():
        count += 1
        if progress_bar: progress_bar.progress(30 + int(count/len(INDICATORS_MAP)*40))
        try:
            indi = fdr.DataReader(code, start_date)
            if indi.empty: continue
            aligned = indi.iloc[:, 0].reindex(stock.index).interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
            indi_norm = (aligned - aligned.min()) / (aligned.max() - aligned.min())
            corr = stock_norm.corr(indi_norm)
            if pd.isna(corr): continue
            results.append({'name': name, 'corr': corr, 'abs_corr': abs(corr)})
        except: continue
    
    if not results: return None

    if status_text: status_text.text("🧠 3/4단계: 최적 비중 계산...")
    if progress_bar: progress_bar.progress(80)
    
    df_res = pd.DataFrame(results)
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
st.sidebar.subheader("Step 2. 경제지표 믹싱")

# 분석 기간 먼저 정의
period_opt = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
sel_period = st.sidebar.select_slider("분석 기간", list(period_opt.keys()), value="2년")
days = period_opt[sel_period]
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

if st.sidebar.button("⚡ AI 최적 조합 찾기", type="primary", use_container_width=True):
    stat = st.sidebar.empty()
    prog = st.sidebar.progress(0)
    res = find_optimal_mix(ticker, start_date, prog, stat)
    stat.empty(); prog.empty()
    
    if res == "NO_CORRELATION": st.sidebar.warning("유의미한 지표 없음")
    elif res:
        st.session_state.opt_data = res
        st.sidebar.success(f"최적 조합 {len(res)}개 발견!")
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

# --- 4. 메인 로직 ---
@st.cache_data
def load_data_mix(stock_code, configs, start):
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
            nm = (align - align.min()) / (align.max() - align.min())
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
    stock, macro, raws, norms = load_data_mix(ticker, configs, start_date)
    
    if stock is not None:
        df = pd.concat([stock, macro], axis=1).dropna()
        df.columns = ['Stock', 'Macro']
        
        # 메인 차트용 정규화
        df['Stock_N'] = (df['Stock'] - df['Stock'].min()) / (df['Stock'].max() - df['Stock'].min())
        df['Macro_N'] = (df['Macro'] - df['Macro'].min()) / (df['Macro'].max() - df['Macro'].min())
        gap = df['Stock_N'].iloc[-1] - df['Macro_N'].iloc[-1]
        
        # --- 메트릭 ---
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
            
        with c2: st.metric("내 매크로 점수", f"{df['Macro'].iloc[-1]:.2f} 점", "0~1 Scale")
        
        with c3:
            if gap > 0.3: st.metric("괴리율 상태", "🔴 과열", f"Gap {gap:.2f}", delta_color="inverse")
            elif gap < -0.3: st.metric("괴리율 상태", "🔵 저평가", f"Gap {gap:.2f}", delta_color="normal")
            else: st.metric("괴리율 상태", "🟢 적정", f"Gap {gap:.2f}", delta_color="off")

        # --- 차트 ---
        st.subheader("📈 추세 비교")
        st.caption("💡 Tip: 차트 하단의 '기간 슬라이더'를 드래그하여 확대/축소할 수 있습니다.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Stock_N'], name='주가(정규화)', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.index, y=df['Macro_N'], name='매크로 모델', line=dict(color='red', dash='dot')))
        fig.update_xaxes(rangeslider_visible=True)
        fig.update_layout(hovermode="x unified", height=400, margin=dict(t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # --- 예측력 검증 (Backtest) ---
        st.markdown("---")
        st.subheader("🔮 이 모델의 예측력 검증 (Backtest)")
        
        analysis_df = pd.DataFrame({
            'Gap': df['Stock_N'] - df['Macro_N'],
            'Next_Return': df['Stock'].pct_change(periods=20).shift(-20) * 100 
        }).dropna()

        if not analysis_df.empty:
            corr_predict = analysis_df['Gap'].corr(analysis_df['Next_Return'])
            
            c_res1, c_res2 = st.columns([1, 2])
            
            with c_res1:
                st.markdown("#### 📊 분석 결과")
                st.metric("예측 상관계수", f"{corr_predict:.2f}", help="-1에 가까울수록 좋습니다.")
                
                if corr_predict < -0.3:
                    st.success("✅ **유효한 모델입니다!**\n\n과거 데이터를 볼 때, 괴리율이 클 때 주가가 하락하는 경향이 있습니다.")
                elif corr_predict > 0.3:
                    st.error("❌ **위험한 모델입니다!**\n\n오히려 고평가일 때 주가가 더 오르는 경향이 있습니다.")
                else:
                    st.warning("⚠️ **예측력이 약합니다.**\n\n뚜렷한 패턴이 없습니다.")

            with c_res2:
                # [수정] 여기서 에러 났던 부분! statsmodels가 없어도 점은 찍히게 처리
                try:
                    fig_scat = px.scatter(
                        analysis_df, x='Gap', y='Next_Return', 
                        trendline="ols", 
                        trendline_color_override="red",
                        title="괴리율(X) vs 1개월 뒤 수익률(Y)",
                        opacity=0.3
                    )
                except:
                    # statsmodels 없으면 추세선 없이 그림
                    fig_scat = px.scatter(
                        analysis_df, x='Gap', y='Next_Return', 
                        title="괴리율(X) vs 1개월 뒤 수익률(Y) (추세선 없음)",
                        opacity=0.3
                    )
                
                fig_scat.update_layout(height=350)
                st.plotly_chart(fig_scat, use_container_width=True)

        # 개별 지표 탭
        with st.expander("📊 개별 지표 상세 보기"):
            cols = st.columns(2)
            for i, name in enumerate(configs.keys()):
                if name in norms:
                    with cols[i%2]:
                        # [수정] make_subplots 임포트했으니 이제 잘 됩니다!
                        fig_sub = make_subplots(specs=[[{"secondary_y": True}]])
                        fig_sub.add_trace(go.Scatter(x=df.index, y=df['Stock_N'], name="주가", line=dict(color='#ccc')), secondary_y=False)
                        fname = f"{name} (역)" if configs[name]['inverse'] else name
                        fig_sub.add_trace(go.Scatter(x=norms[name].index, y=norms[name], name=fname, line=dict(color='blue')), secondary_y=True)
                        fig_sub.update_layout(title=name, height=250, showlegend=False, margin=dict(t=30,b=0))
                        fig_sub.update_yaxes(showticklabels=False)
                        st.plotly_chart(fig_sub, use_container_width=True)

    else: st.error("데이터 없음")
