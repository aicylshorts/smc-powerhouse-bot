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
    Basic but functional SMC setup detector.
    Looks for liquidity sweep (inducement) + FVG + basic structure shift.
    Returns dict with trade params if high probability setup found, else None.
    '''
    if len(df) < 30:
        return None

    # Get recent data
    recent = df.iloc[-20:]
    close = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    high = df['high'].iloc[-1]
    low = df['low'].iloc[-1]

    # Detect swings for liquidity
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()

    # Simple liquidity sweep detection (price wicks beyond swing then closes back)
    sweep_bullish = (low < swing_low * 0.999) and (close > prev_close)
    sweep_bearish = (high > swing_high * 1.001) and (close < prev_close)

    # Detect FVGs
    fvgs = detect_fvg(df.iloc[-10:])  # recent FVGs
    has_bullish_fvg = any(f['type'] == 'bullish' for f in fvgs)
    has_bearish_fvg = any(f['type'] == 'bearish' for f in fvgs)

    # Basic BOS/CHOCH proxy: break of recent structure
    bos_bullish = close > swing_high * 0.998
    bos_bearish = close < swing_low * 1.002

    # Determine direction and score
    if sweep_bullish and has_bullish_fvg:
        direction = 'BUY'
        entry = close
        sl = min(swing_low, low) * 0.995
        rr = 2.5
        tp1 = entry + (entry - sl) * 1.5
        tp2 = entry + (entry - sl) * rr
        score = calculate_confluence_score(sweep=True, fvg=True, ob=True, bos=bos_bullish, multi_tf=True)
    elif sweep_bearish and has_bearish_fvg:
        direction = 'SELL'
        entry = close
        sl = max(swing_high, high) * 1.005
        rr = 2.5
        tp1 = entry - (sl - entry) * 1.5
        tp2 = entry - (sl - entry) * rr
        score = calculate_confluence_score(sweep=True, fvg=True, ob=True, bos=bos_bearish, multi_tf=True)
    else:
        return None

    if score < 65:
        return None

    return {
        'direction': direction,
        'entry': round(entry, 5),
        'sl': round(sl, 5),
        'tp1': round(tp1, 5),
        'tp2': round(tp2, 5),
        'score': int(score)
    }
