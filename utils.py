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


def detect_order_block(df: pd.DataFrame, direction: str, lookback=15):
    if len(df) < lookback + 6:
        return None
    recent = df.iloc[-(lookback + 6):].reset_index(drop=True)

    if direction == 'bullish':
        for i in range(len(recent) - 4, 1, -1):
            if recent['close'].iloc[i] < recent['open'].iloc[i]:
                candle_body = abs(recent['close'].iloc[i] - recent['open'].iloc[i])
                move_after = recent['close'].iloc[i+1] - recent['close'].iloc[i]
                if move_after > candle_body * 1.8:
                    return {'type': 'bullish_ob', 'low': recent['low'].iloc[i], 'high': recent['high'].iloc[i], 'mitigation_level': recent['high'].iloc[i]}
    else:
        for i in range(len(recent) - 4, 1, -1):
            if recent['close'].iloc[i] > recent['open'].iloc[i]:
                candle_body = abs(recent['close'].iloc[i] - recent['open'].iloc[i])
                move_after = recent['close'].iloc[i] - recent['close'].iloc[i+1]
                if move_after > candle_body * 1.8:
                    return {'type': 'bearish_ob', 'low': recent['low'].iloc[i], 'high': recent['high'].iloc[i], 'mitigation_level': recent['low'].iloc[i]}
    return None


def calculate_confluence_score(sweep=False, fvg=False, ob=False, bos=False, displacement=False, htf_alignment=False, ob_mitigated=False, real_sweep=False, mss=False):
    score = 0
    if sweep: score += 20
    if fvg: score += 18
    if ob: score += 22
    if ob_mitigated: score += 8
    if real_sweep: score += 12      # Bonus for real (non-inducement) sweep
    if mss: score += 12             # Market Structure Shift
    if displacement: score += 8
    if htf_alignment: score += 8
    if bos: score += 5
    return min(score, 100)


def detect_smc_setup(df: pd.DataFrame, symbol: str, tf: str, htf_df: pd.DataFrame = None):
    if len(df) < 45:
        return None

    recent = df.iloc[-30:]
    close = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    high = df['high'].iloc[-1]
    low = df['low'].iloc[-1]

    swing_high = recent['high'].max()
    swing_low = recent['low'].min()

    # Liquidity Sweep
    sweep_bullish = (low < swing_low * 0.998) and (close > prev_close)
    sweep_bearish = (high > swing_high * 1.002) and (close < prev_close)

    # Check if it's a REAL sweep (strong follow-through) vs inducement
    real_sweep_bullish = sweep_bullish and (close - low) > (swing_high - swing_low) * 0.35
    real_sweep_bearish = sweep_bearish and (high - close) > (swing_high - swing_low) * 0.35

    fvgs = detect_fvg(df.iloc[-12:])
    has_bullish_fvg = any(f['type'] == 'bullish' for f in fvgs)
    has_bearish_fvg = any(f['type'] == 'bearish' for f in fvgs)

    if sweep_bullish and has_bullish_fvg:
        direction = 'BUY'
        entry = close
        sl = min(swing_low, low) * 0.994
        raw_risk = entry - sl

        ob = detect_order_block(df, 'bullish')
        has_ob = ob is not None
        ob_mitigated = has_ob and (ob['low'] <= entry <= ob['high'] * 1.005)

        displacement = (close - low) > (swing_high - swing_low) * 0.3

        # Market Structure Shift (MSS) - price breaks previous swing in direction of move
        mss = close > swing_high * 0.997

        htf_alignment = False
        if htf_df is not None and len(htf_df) > 20:
            htf_recent = htf_df.iloc[-10:]
            if close > htf_recent['close'].iloc[0]:
                htf_alignment = True

        score = calculate_confluence_score(
            sweep=True, fvg=True, ob=has_ob, ob_mitigated=ob_mitigated,
            real_sweep=real_sweep_bullish, mss=mss,
            displacement=displacement, htf_alignment=htf_alignment
        )

    elif sweep_bearish and has_bearish_fvg:
        direction = 'SELL'
        entry = close
        sl = max(swing_high, high) * 1.006
        raw_risk = sl - entry

        ob = detect_order_block(df, 'bearish')
        has_ob = ob is not None
        ob_mitigated = has_ob and (ob['low'] * 0.995 <= entry <= ob['high'])

        displacement = (high - close) > (swing_high - swing_low) * 0.3

        mss = close < swing_low * 1.003

        htf_alignment = False
        if htf_df is not None and len(htf_df) > 20:
            htf_recent = htf_df.iloc[-10:]
            if close < htf_recent['close'].iloc[0]:
                htf_alignment = True

        score = calculate_confluence_score(
            sweep=True, fvg=True, ob=has_ob, ob_mitigated=ob_mitigated,
            real_sweep=real_sweep_bearish, mss=mss,
            displacement=displacement, htf_alignment=htf_alignment
        )
    else:
        return None

    if score < 78:   # Slightly raised threshold for quality
        return None

    if score >= 92:
        tp1_mult, tp2_mult, tp3_mult = 2.0, 3.8, 5.5
    elif score >= 85:
        tp1_mult, tp2_mult, tp3_mult = 1.7, 3.4, 5.0
    else:
        tp1_mult, tp2_mult, tp3_mult = 1.5, 3.0, 4.2

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
