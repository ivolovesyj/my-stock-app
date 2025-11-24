import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# --- 3. [수정됨] 복합 지표 설정 (안전한 영어 변수명 사용) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 경제지표 믹싱 (Total 100%)")

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
    "사용할 지표를 고르세요",
    list(indicators_map.keys()),
    default=st.session_state.selected_inds
)

# N빵 계산
default_weight = 100.0 / len(selected_keys) if selected_keys else 0

table_data = []
for key in selected_keys:
    default_inverse = True if key in ["미국 10년물 금리", "원/달러 환율", "국제유가(WTI)", "미국 기준금리", "VIX (공포지수)"] else False
    # [수정] 컬럼명을 영어(Weight, Inverse)로 변경하여 에러 방지
    table_data.append({
        "Name": key, 
        "Weight": float(f"{default_weight:.1f}"),
        "Inverse": default_inverse
    })

df_config = pd.DataFrame(table_data)

st.sidebar.caption("👇 합계 100%가 되도록 비중을 조절하세요.")
edited_df = st.sidebar.data_editor(
    df_config,
    column_config={
        "Name": st.column_config.TextColumn("지표명", disabled=True), # 보여질 땐 한글
        "Weight": st.column_config.NumberColumn("비중(%)", min_value=0, max_value=100, step=1, format="%d%%"), # 보여질 땐 비중(%)
        "Inverse": st.column_config.CheckboxColumn("역방향 적용?")
    },
    hide_index=True,
    use_container_width=True
)

# [수정] 영어 컬럼명 'Weight'로 접근 (안전함)
total_sum = edited_df["Weight"].sum()
remaining = 100 - total_sum

if abs(remaining) < 0.1:
    st.sidebar.success(f"✅ 총합 100% (완벽합니다!)")
    is_valid_total = True
else:
    if remaining > 0:
        st.sidebar.warning(f"⚠️ 현재 {total_sum:.0f}% (부족: +{remaining:.0f}%)")
    else:
        st.sidebar.error(f"🚫 현재 {total_sum:.0f}% (초과: {remaining:.0f}%)")
    is_valid_total = False

# 설정값 변환
configs = {}
for index, row in edited_df.iterrows():
    name = row["Name"]
    configs[name] = {'code': indicators_map[name], 'weight': row["Weight"], 'inverse': row["Inverse"]}

st.sidebar.markdown("---")
period_options = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095, "5년": 1825}
selected_period = st.sidebar.radio("기간", list(period_options.keys()), index=2, horizontal=True)
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
            
            if conf['inverse']:
                norm = 1 - norm
            
            normalized_indicators[name] = norm

            macro_score = macro_score.add(norm * conf['weight'], fill_value=0)
            total_weight += conf['weight']
        except:
            pass
            
    if total_weight > 0:
        final_macro_index = macro_score / total_weight
    else:
        final_macro_index = pd.Series(0, index=stock.index)

    return stock, final_macro_index, loaded_indicators, normalized_indicators

# --- 5. 메인 화면 ---
composite_name = "나만의 매크로 지수 (Custom Macro Index)"
st.title(f"📈 {display_name} vs {composite_name}")

if not configs:
    st.warning("👈 사이드바에서 경제지표를 최소 1개 이상 선택해주세요.")
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

        tags = ""
        for k, v in configs.items():
            arrow = "🔄역" if v['inverse'] else "⬆️정"
            tags += f"`{k} ({v['weight']}%, {arrow})` "
        st.markdown(f"### 📊 모델 구성: {tags}")
        
        if not is_valid_total:
             st.caption(f"⚠️ 주의: 현재 비중 합계가 {total_sum}% 입니다. 100%를 맞추면 더 정확한 분석이 가능합니다.")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name='주가 (정규화)', line=dict(color='blue', width=2)))
        fig.add_trace(go.Scatter(x=df_final.index, y=df_final['Macro_Norm'], name='내 매크로 지수', line=dict(color='red', width=2, dash='dot')))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 합치기 전, 개별 지표 vs 주가 비교 (Click)", expanded=True):
            st.caption("파란색(왼쪽 축): 주가(정규화) / 빨간 점선(오른쪽 축): 해당 지표의 점수")
            
            for name in configs.keys():
                if name in raw_indicators and name in norm_indicators:
                    st.subheader(f"📌 주가 vs {name}")
                    
                    sub_fig = make_subplots(specs=[[{"secondary_y": True}]])
                    sub_fig.add_trace(
                        go.Scatter(x=df_final.index, y=df_final['Stock_Norm'], name="주가 (정규화)", line=dict(color='blue', width=1.5)),
                        secondary_y=False
                    )
                    score_name = "지표 점수 (역방향)" if configs[name]['inverse'] else "지표 점수 (정방향)"
                    sub_fig.add_trace(
                        go.Scatter(x=norm_indicators[name].index, y=norm_indicators[name], name=score_name, line=dict(color='red', width=2, dash='dot')),
                        secondary_y=True
                    )
                    sub_fig.update_yaxes(title_text="주가 추세", secondary_y=False)
                    sub_fig.update_yaxes(title_text="지표 점수 (0~1)", secondary_y=True, range=[0, 1.1])
                    sub_fig.update_layout(height=350, margin=dict(t=30, b=20))
                    st.plotly_chart(sub_fig, use_container_width=True)

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

    else:
        st.error("데이터 로딩 실패. 종목 코드나 날짜를 확인해주세요.")
