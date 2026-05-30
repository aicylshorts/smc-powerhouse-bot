import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from utils import detect_smc_setup

load_dotenv()

OANDA_TOKEN = os.getenv('OANDA_TOKEN')


def fetch_historical_data(instrument, granularity='M15', days=30):
    '''Fetch historical candles from OANDA Practice'''
    url = f'https://api-fxtrade-practice.oanda.com/v3/instruments/{instrument}/candles'
    headers = {
        'Authorization': f'Bearer {OANDA_TOKEN}',
        'Content-Type': 'application/json'
    }

    end = datetime.utcnow()
    start = end - timedelta(days=days)

    params = {
        'granularity': granularity,
        'from': start.isoformat() + 'Z',
        'to': end.isoformat() + 'Z',
        'price': 'M'
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get('candles', [])

        if not data:
            print("No data returned from OANDA.")
            return pd.DataFrame()

        df = pd.DataFrame([{
            'time': pd.to_datetime(c['time']),
            'open': float(c['mid']['o']),
            'high': float(c['mid']['h']),
            'low': float(c['mid']['l']),
            'close': float(c['mid']['c'])
        } for c in data])

        df.set_index('time', inplace=True)
        return df

    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()


def run_backtest(instrument='XAU_USD', granularity='M15', days=30):
    print(f"\n=== Backtesting {instrument} on {granularity} for last {days} days ===\n")

    df = fetch_historical_data(instrument, granularity, days)
    if df.empty:
        print("No data available for backtest.")
        return

    trades = []
    equity = 1000
    peak = equity
    max_drawdown = 0

    for i in range(50, len(df)):
        window = df.iloc[:i+1]
        setup = detect_smc_setup(window, instrument, granularity)

        if setup:
            direction = setup['direction']
            entry = setup['entry']
            sl = setup['sl']
            tp2 = setup['tp2']
            score = setup['score']

            future = df.iloc[i+1:]

            if direction == 'BUY':
                hit_tp = future[future['high'] >= tp2]
                hit_sl = future[future['low'] <= sl]
            else:
                hit_tp = future[future['low'] <= tp2]
                hit_sl = future[future['high'] >= sl]

            if not hit_tp.empty and (hit_sl.empty or hit_tp.index[0] < hit_sl.index[0]):
                result = 'WIN'
                rr = 3.0
                equity += (equity * 0.01 * rr)
            else:
                result = 'LOSS'
                rr = -1.0
                equity += (equity * 0.01 * rr)

            peak = max(peak, equity)
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)

            trades.append({
                'time': df.index[i],
                'direction': direction,
                'entry': entry,
                'sl': sl,
                'tp2': tp2,
                'score': score,
                'result': result,
                'rr': rr
            })

    if not trades:
        print("No trades generated during backtest period.")
        return

    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['result'] == 'WIN'])
    losses = len(df_trades[df_trades['result'] == 'LOSS'])
    win_rate = (wins / len(df_trades)) * 100 if trades else 0

    avg_rr = df_trades['rr'].mean()
    profit_factor = abs(df_trades[df_trades['rr'] > 0]['rr'].sum() / df_trades[df_trades['rr'] < 0]['rr'].sum()) if losses > 0 else float('inf')

    print(f"Total Trades: {len(trades)}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Average RR: {avg_rr:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max Drawdown: {max_drawdown*100:.2f}%")
    print(f"Final Equity (simulated 1% risk): ${equity:.2f}")

    return df_trades


if __name__ == "__main__":
    run_backtest(instrument='XAU_USD', granularity='M15', days=60)
