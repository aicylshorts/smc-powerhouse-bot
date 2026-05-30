import pandas as pd

def detect_fvg(df: pd.DataFrame):
    '''Detect Fair Value Gaps'''
    fvgs = []
    for i in range(len(df)-2):
        if df['low'].iloc[i+2] > df['high'].iloc[i]:
            fvgs.append({'type': 'bullish', 'low': df['low'].iloc[i], 'high': df['low'].iloc[i+2]})
        elif df['high'].iloc[i+2] < df['low'].iloc[i]:
            fvgs.append({'type': 'bearish', 'low': df['high'].iloc[i+2], 'high': df['high'].iloc[i]})
    return fvgs

def calculate_confluence_score(sweep=False, fvg=False, ob=False, bos=False, multi_tf=False):
    score = 0
    if sweep: score += 30
    if fvg: score += 25
    if ob: score += 20
    if bos: score += 15
    if multi_tf: score += 10
    return min(score, 100)
