import pandas as pd
import numpy as np

def detect_fvg(df: pd.DataFrame):
    fvgs = []
    for i in range(len(df)-2):
        if df['low'].iloc[i+2] > df['high'].iloc[i]:
            fvgs.append({'type': 'bullish', 'low': df['low'].iloc[i], 'high': df['low'].iloc[i+2]})
        elif df['high'].iloc[i+2] < df['low'].iloc[i]:
            fvgs.append({'type': 'bearish', 'low': df['high'].iloc[i+2], 'high': df['high'].iloc[i]})
    return fvgs


def detect_order_block(df: pd.DataFrame, direction: str, lookback=10):
    '''Simple Order Block detection (last opposing candle before strong move)'''
    if len(df) < lookback + 5:
        return None

    recent = df.iloc[-(lookback+5):]

    if direction == 'bullish':
        for i in range(len(recent)-3, 0, -1):
            # Last bearish candle before strong bullish move
            if recent['close'].iloc[i] < recent['open'].iloc[i]:
                body_size = abs(recent['close'].iloc[i] - recent['open'].iloc[i])
                next_move = recent['close'].iloc[i+1] - recent['close'].iloc[i]
                if next_move > body_size * 1.5:  # Strong displacement after
                    return {'type': 'bullish', 'low': recent['low'].iloc[i], 'high': recent['high'].iloc[i]}
    else:
        for i in range(len(recent)-3, 0, -1):
            if recent['close'].iloc[i] > recent['open'].iloc[i]:
                body_size = abs(recent['close'].iloc[i] - recent['open'].iloc[i])
                next_move = recent['close'].iloc[i] - recent['close'].iloc[i+1]
                if next_move > body_size * 1.5:
                    return {'type': 'bearish', 'low': recent['low'].iloc[i], 'high': recent['high'].iloc[i]}
    return None


def calculate_confluence_score(sweep=False, fvg=False, ob=False, bos=False, multi_tf=False, displacement=False):
    score = 0
    if sweep: score += 25
    if fvg: score += 20
    if ob: score += 25      # Order Block is high value
    if bos: score += 15
    if displacement: score += 10
    if multi_tf: score += 5
    return min(score, 100)


def detect_smc_setup(df: pd.DataFrame, symbol: str, tf: str):
    if len(df) < 40:
        return None

    recent = df.iloc[-25:]
    close = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    high = df['high'].iloc[-1]
    low = df['low'].iloc[-1]

    swing_high = recent['high'].max()
    swing_low = recent['low'].min()

    # Liquidity Sweep
    sweep_bullish = (low < swing_low * 0.998) and (close > prev_close) and (close - low > (swing_high - swing_low) * 0.3)
    sweep_bearish = (high > swing_high * 1.002) and (close < prev_close) and (high - close > (swing_high - swing_low) * 0.3)

    fvgs = detect_fvg(df.iloc[-12:])
    has_bullish_fvg = any(f['type'] == 'bullish' for f in fvgs)
    has_bearish_fvg = any(f['type'] == 'bearish' for f in fvgs)

    if sweep_bullish and has_bullish_fvg:
        direction = 'BUY'
        entry = close
        sl = min(swing_low, low) * 0.994
        raw_risk = entry - sl
        ob = detect_order_block(df, 'bullish')
        has_ob = ob is not None and ob['low'] <= entry <= ob['high'] * 1.002
        displacement = (close - low) > (swing_high - swing_low) * 0.25
        score = calculate_confluence_score(sweep=True, fvg=True, ob=has_ob, bos=True, displacement=displacement)

    elif sweep_bearish and has_bearish_fvg:
        direction = 'SELL'
        entry = close
        sl = max(swing_high, high) * 1.006
        raw_risk = sl - entry
        ob = detect_order_block(df, 'bearish')
        has_ob = ob is not None and ob['low'] * 0.998 <= entry <= ob['high']
        displacement = (high - close) > (swing_high - swing_low) * 0.25
        score = calculate_confluence_score(sweep=True, fvg=True, ob=has_ob, bos=True, displacement=displacement)
    else:
        return None

    if score < 75:
        return None

    # Dynamic 3 TPs
    if score >= 90:
        tp1_mult, tp2_mult, tp3_mult = 1.8, 3.5, 5.0
    elif score >= 83:
        tp1_mult, tp2_mult, tp3_mult = 1.6, 3.2, 4.5
    else:
        tp1_mult, tp2_mult, tp3_mult = 1.5, 2.8, 4.0

    if direction == 'BUY':
        tp1 = entry + raw_risk * tp1_mult
        tp2 = entry + raw_risk * tp2_mult
        tp3 = entry + raw_risk * tp3_mult
    else:
        tp1 = entry - raw_risk * tp1_mult
        tp2 = entry - raw_risk * tp2_mult
        tp3 = entry - raw_risk * tp3_mult

    return {
        'direction': direction,
        'entry': round(entry, 5),
        'sl': round(sl, 5),
        'tp1': round(tp1, 5),
        'tp2': round(tp2, 5),
        'tp3': round(tp3, 5),
        'score': int(score),
        'tp1_r': tp1_mult,
        'tp2_r': tp2_mult,
        'tp3_r': tp3_mult
    }
