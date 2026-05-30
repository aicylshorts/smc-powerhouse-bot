import pandas as pd
import numpy as np

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


def detect_smc_setup(df: pd.DataFrame, symbol: str, tf: str):
    '''
    Mulham-style SMC detection with dynamic RR.
    Stronger setups get better RR.
    Very strong setups (90+) get 3 TPs.
    '''
    if len(df) < 40:
        return None

    recent = df.iloc[-25:]
    close = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    high = df['high'].iloc[-1]
    low = df['low'].iloc[-1]

    swing_high = recent['high'].max()
    swing_low = recent['low'].min()

    # Stricter liquidity sweep
    sweep_bullish = (low < swing_low * 0.998) and (close > prev_close) and (close - low > (swing_high - swing_low) * 0.3)
    sweep_bearish = (high > swing_high * 1.002) and (close < prev_close) and (high - close > (swing_high - swing_low) * 0.3)

    fvgs = detect_fvg(df.iloc[-12:])
    has_bullish_fvg = any(f['type'] == 'bullish' for f in fvgs)
    has_bearish_fvg = any(f['type'] == 'bearish' for f in fvgs)

    bos_bullish = close > swing_high * 0.997
    bos_bearish = close < swing_low * 1.003

    if sweep_bullish and has_bullish_fvg:
        direction = 'BUY'
        entry = close
        sl = min(swing_low, low) * 0.994
        raw_risk = entry - sl
        score = calculate_confluence_score(sweep=True, fvg=True, ob=True, bos=bos_bullish, multi_tf=True)

    elif sweep_bearish and has_bearish_fvg:
        direction = 'SELL'
        entry = close
        sl = max(swing_high, high) * 1.006
        raw_risk = sl - entry
        score = calculate_confluence_score(sweep=True, fvg=True, ob=True, bos=bos_bearish, multi_tf=True)
    else:
        return None

    if score < 75:
        return None

    # Dynamic RR based on strength
    if score >= 90:
        # Very strong setup → 3 TPs
        tp1 = entry + raw_risk * 1.8 if direction == 'BUY' else entry - raw_risk * 1.8
        tp2 = entry + raw_risk * 3.5 if direction == 'BUY' else entry - raw_risk * 3.5
        tp3 = entry + raw_risk * 4.8 if direction == 'BUY' else entry - raw_risk * 4.8
        tp1_r, tp2_r, tp3_r = 1.8, 3.5, 4.8
    elif score >= 83:
        tp1 = entry + raw_risk * 1.7 if direction == 'BUY' else entry - raw_risk * 1.7
        tp2 = entry + raw_risk * 3.3 if direction == 'BUY' else entry - raw_risk * 3.3
        tp3 = None
        tp1_r, tp2_r, tp3_r = 1.7, 3.3, None
    else:
        tp1 = entry + raw_risk * 1.6 if direction == 'BUY' else entry - raw_risk * 1.6
        tp2 = entry + raw_risk * 3.0 if direction == 'BUY' else entry - raw_risk * 3.0
        tp3 = None
        tp1_r, tp2_r, tp3_r = 1.6, 3.0, None

    result = {
        'direction': direction,
        'entry': round(entry, 5),
        'sl': round(sl, 5),
        'tp1': round(tp1, 5),
        'tp2': round(tp2, 5),
        'score': int(score),
        'tp1_r': tp1_r,
        'tp2_r': tp2_r,
    }

    if tp3 is not None:
        result['tp3'] = round(tp3, 5)
        result['tp3_r'] = tp3_r

    return result
