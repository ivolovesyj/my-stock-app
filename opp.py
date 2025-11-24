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
            
            # 시차 적용
            shifted_align = align.shift(lag) 
            
            # 정규화
            nm = (shifted_align - shifted_align.min()) / (shifted_align.max() - shifted_align.min())

            if conf['inverse']: nm = 1 - nm
            norms[name] = nm
            
            # 가중치 합산
            macro = macro.add(nm * conf['weight'], fill_value=0)
            total_w += conf['weight']
        except: pass
        
    if total_weight > 0:
        final_macro = macro / total_w
        
        # [FIX] 여기가 수정된 핵심입니다! 
        # 시차(Lag) 때문에 생긴 앞/뒤의 0.0 값을 NaN(결측치)으로 바꿔서
        # 나중에 dropna() 될 때 깔끔하게 사라지도록 합니다.
        if lag > 0:
            final_macro.iloc[:lag] = np.nan  # 앞부분 잘라내기
        elif lag < 0:
            final_macro.iloc[lag:] = np.nan  # 뒷부분 잘라내기
            
    else:
        final_macro = pd.Series(0, index=stock.index)

    return stock, final_macro, raws, norms
