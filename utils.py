import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple

def detect_fvg(df: pd.DataFrame, lookback: int = 25) -> List[Dict]:
    """
    Detect Fair Value Gaps (imbalances) more accurately.
    A bullish FVG exists when candle[i+2].low > candle[i].high
    A bearish FVG exists when candle[i+2].high < candle[i].low
    """
    fvgs = []
    if len(df) < 3:
        return fvgs
    
    for i in range(len(df) - 2):
        c1_high = df['high'].iloc[i]
        c1_low = df['low'].iloc[i]
        c3_high = df['high'].iloc[i + 2]
        c3_low = df['low'].iloc[i + 2]
        
        if c3_low > c1_high:  # Bullish FVG
            fvgs.append({
                'type': 'bullish',
                'low': c1_high,
                'high': c3_low,
                'index': i + 1
            })
        elif c3_high < c1_low:  # Bearish FVG
            fvgs.append({
                'type': 'bearish',
                'low': c3_high,
                'high': c1_low,
                'index': i + 1
            })
    
    return fvgs[-lookback:] if fvgs else []


def is_fvg_mitigated(fvgs: List[Dict], current_price: float, direction: str) -> bool:
    """Check if price has entered (mitigated) any relevant FVG."""
    for fvg in fvgs:
        if direction == 'bullish' and fvg['type'] == 'bullish':
            if fvg['low'] <= current_price <= fvg['high']:
                return True
        elif direction == 'bearish' and fvg['type'] == 'bearish':
            if fvg['low'] <= current_price <= fvg['high']:
                return True
    return False


def detect_liquidity_sweep(df: pd.DataFrame, direction: str) -> Tuple[bool, bool, float]:
    """
    Improved liquidity sweep detection.
    Returns: (real_sweep, any_sweep, displacement_strength)
    Requires meaningful displacement after sweeping recent swing.
    """
    if len(df) < 12:
        return False, False, 0.0
    
    recent = df.iloc[-12:]
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    
    current_close = df['close'].iloc[-1]
    current_low = df['low'].iloc[-1]
    current_high = df['high'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    
    atr_approx = (recent['high'] - recent['low']).mean()
    
    if direction == 'bullish':
        swept = current_low < swing_low * 0.9995
        displacement = (current_close - current_low) / max(atr_approx, 1e-9)
        strong_displacement = displacement > 0.6  # Stricter
        real_sweep = swept and strong_displacement and current_close > prev_close * 1.0005
        return real_sweep, swept, round(displacement, 2)
    
    else:  # bearish
        swept = current_high > swing_high * 1.0005
        displacement = (current_high - current_close) / max(atr_approx, 1e-9)
        strong_displacement = displacement > 0.6
        real_sweep = swept and strong_displacement and current_close < prev_close * 0.9995
        return real_sweep, swept, round(displacement, 2)


def detect_order_block(df: pd.DataFrame, direction: str, lookback: int = 14) -> Optional[Dict]:
    """
    Detect last opposing candle before strong displacement (Order Block).
    """
    if len(df) < lookback + 6:
        return None
    
    recent = df.iloc[-(lookback + 6):].reset_index(drop=True)
    
    for i in range(len(recent) - 5, 2, -1):
        candle = recent.iloc[i]
        body_size = abs(candle['close'] - candle['open'])
        
        if direction == 'bullish' and candle['close'] < candle['open']:  # Bearish candle
            move_after = recent['close'].iloc[i + 1] - candle['close']
            if move_after > body_size * 1.6:  # Strong impulsive move after
                return {
                    'type': 'bullish_ob',
                    'low': float(candle['low']),
                    'high': float(candle['high']),
                    'mitigation_level': float(candle['high'])
                }
        elif direction == 'bearish' and candle['close'] > candle['open']:  # Bullish candle
            move_after = candle['close'] - recent['close'].iloc[i + 1]
            if move_after > body_size * 1.6:
                return {
                    'type': 'bearish_ob',
                    'low': float(candle['low']),
                    'high': float(candle['high']),
                    'mitigation_level': float(candle['low'])
                }
    return None


def detect_bos(df: pd.DataFrame, direction: str) -> bool:
    """Basic Break of Structure detection for confirmation."""
    if len(df) < 18:
        return False
    
    recent = df.iloc[-18:]
    
    if direction == 'bullish':
        prior_swing_high = recent['high'].iloc[:-4].max()
        return df['close'].iloc[-1] > prior_swing_high
    else:
        prior_swing_low = recent['low'].iloc[:-4].min()
        return df['close'].iloc[-1] < prior_swing_low


def calculate_confluence_score(
    real_sweep: bool = False,
    fvg: bool = False,
    fvg_mitigated: bool = False,
    ob: bool = False,
    ob_mitigated: bool = False,
    bos: bool = False,
    displacement: bool = False,
    htf_alignment: bool = False,
    strong_displacement: bool = False
) -> int:
    """
    Stricter confluence scoring.
    High scores now require multiple high-quality confluences.
    """
    score = 0
    
    if real_sweep:
        score += 20          # Highest weight - true inducement sweep
    if fvg:
        score += 17          # Core imbalance
    if fvg_mitigated:
        score += 5
    if ob:
        score += 19          # Strong institutional level
    if ob_mitigated:
        score += 6
    if bos:
        score += 14          # Structure break confirmation
    if strong_displacement:
        score += 12
    if displacement:
        score += 8
    if htf_alignment:
        score += 9
    
    return min(score, 100)


def detect_smc_setup(df: pd.DataFrame, symbol: str, tf: str, htf_df: pd.DataFrame = None) -> Optional[Dict]:
    """
    Main SMC setup detector.
    Requires liquidity sweep + FVG as base.
    Uses stricter internal scoring. Returns setup only if score >= 70.
    """
    if len(df) < 50:
        return None

    close = float(df['close'].iloc[-1])
    high = float(df['high'].iloc[-1])
    low = float(df['low'].iloc[-1])
    prev_close = float(df['close'].iloc[-2])

    # --- Liquidity Sweep Analysis ---
    real_sweep_bull, any_sweep_bull, disp_bull = detect_liquidity_sweep(df, 'bullish')
    real_sweep_bear, any_sweep_bear, disp_bear = detect_liquidity_sweep(df, 'bearish')

    # --- FVG Analysis ---
    recent_fvgs = detect_fvg(df.iloc[-20:])
    has_bullish_fvg = any(f['type'] == 'bullish' for f in recent_fvgs)
    has_bearish_fvg = any(f['type'] == 'bearish' for f in recent_fvgs)

    fvg_mitigated_bull = is_fvg_mitigated(recent_fvgs, close, 'bullish') if has_bullish_fvg else False
    fvg_mitigated_bear = is_fvg_mitigated(recent_fvgs, close, 'bearish') if has_bearish_fvg else False

    setup = None

    # === BULLISH SETUP ===
    if real_sweep_bull and has_bullish_fvg:
        direction = 'BUY'
        entry = close
        
        # SL below the swept low with buffer
        swing_low = df['low'].iloc[-12:].min()
        sl = float(min(swing_low, low) * 0.995)
        raw_risk = entry - sl

        ob = detect_order_block(df, 'bullish')
        has_ob = ob is not None
        ob_mitigated = has_ob and (ob['low'] <= entry <= ob['high'] * 1.008)

        has_bos = detect_bos(df, 'bullish')
        strong_disp = disp_bull > 0.6

        displacement = (close - low) > (df['high'].iloc[-12:].max() - df['low'].iloc[-12:].min()) * 0.28

        htf_alignment = False
        if htf_df is not None and len(htf_df) > 15:
            if close > float(htf_df['close'].iloc[-6]):
                htf_alignment = True

        score = calculate_confluence_score(
            real_sweep=real_sweep_bull,
            fvg=has_bullish_fvg,
            fvg_mitigated=fvg_mitigated_bull,
            ob=has_ob,
            ob_mitigated=ob_mitigated,
            bos=has_bos,
            displacement=displacement,
            htf_alignment=htf_alignment,
            strong_displacement=strong_disp
        )

        if score >= 70:
            # Dynamic TPs based on score
            if score >= 92:
                tp1_mult, tp2_mult, tp3_mult = 2.1, 4.0, 5.8
            elif score >= 85:
                tp1_mult, tp2_mult, tp3_mult = 1.8, 3.5, 5.2
            elif score >= 78:
                tp1_mult, tp2_mult, tp3_mult = 1.6, 3.1, 4.6
            else:
                tp1_mult, tp2_mult, tp3_mult = 1.5, 2.9, 4.3

            tp1 = entry + raw_risk * tp1_mult
            tp2 = entry + raw_risk * tp2_mult
            tp3 = entry + raw_risk * tp3_mult

            setup = {
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

    # === BEARISH SETUP ===
    elif real_sweep_bear and has_bearish_fvg:
        direction = 'SELL'
        entry = close
        
        swing_high = df['high'].iloc[-12:].max()
        sl = float(max(swing_high, high) * 1.005)
        raw_risk = sl - entry

        ob = detect_order_block(df, 'bearish')
        has_ob = ob is not None
        ob_mitigated = has_ob and (ob['low'] * 0.992 <= entry <= ob['high'])

        has_bos = detect_bos(df, 'bearish')
        strong_disp = disp_bear > 0.6

        displacement = (high - close) > (df['high'].iloc[-12:].max() - df['low'].iloc[-12:].min()) * 0.28

        htf_alignment = False
        if htf_df is not None and len(htf_df) > 15:
            if close < float(htf_df['close'].iloc[-6]):
                htf_alignment = True

        score = calculate_confluence_score(
            real_sweep=real_sweep_bear,
            fvg=has_bearish_fvg,
            fvg_mitigated=fvg_mitigated_bear,
            ob=has_ob,
            ob_mitigated=ob_mitigated,
            bos=has_bos,
            displacement=displacement,
            htf_alignment=htf_alignment,
            strong_displacement=strong_disp
        )

        if score >= 70:
            if score >= 92:
                tp1_mult, tp2_mult, tp3_mult = 2.1, 4.0, 5.8
            elif score >= 85:
                tp1_mult, tp2_mult, tp3_mult = 1.8, 3.5, 5.2
            elif score >= 78:
                tp1_mult, tp2_mult, tp3_mult = 1.6, 3.1, 4.6
            else:
                tp1_mult, tp2_mult, tp3_mult = 1.5, 2.9, 4.3

            tp1 = entry - raw_risk * tp1_mult
            tp2 = entry - raw_risk * tp2_mult
            tp3 = entry - raw_risk * tp3_mult

            setup = {
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

    return setup
