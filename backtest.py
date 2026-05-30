import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from utils import detect_smc_setup

load_dotenv()

OANDA_TOKEN = os.getenv('OANDA_TOKEN')

PAIRS_TO_TEST = [
    'XAU_USD',
    'EUR_USD',
    'GBP_USD',
    'USD_JPY',
    'NAS100_USD'
]


def fetch_historical_data(instrument, granularity='M15', days=30):
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
        print(f"Error fetching {instrument}: {e}")
        return pd.DataFrame()


def run_single_backtest(instrument, granularity='M15', days=30):
    df = fetch_historical_data(instrument, granularity, days)
    if df.empty:
        return None

    trades = []
    for i in range(50, len(df)):
        window = df.iloc[:i+1]
        setup = detect_smc_setup(window, instrument, granularity)

        if setup:
            direction = setup['direction']
            entry = setup['entry']
            sl = setup['sl']
            tp2 = setup['tp2']

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
            else:
                result = 'LOSS'
                rr = -1.0

            trades.append({'result': result, 'rr': rr})

    if not trades:
        return None

    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['result'] == 'WIN'])
    total = len(df_trades)
    win_rate = (wins / total) * 100
    avg_rr = df_trades['rr'].mean()

    return {
        'pair': instrument,
        'trades': total,
        'wins': wins,
        'win_rate': round(win_rate, 2),
        'avg_rr': round(avg_rr, 2)
    }


def run_full_backtest(days=30):
    print(f"\n{'='*60}")
    print(f"BACKTEST RESULTS - Last {days} days")
    print(f"{'='*60}\n")

    results = []
    for pair in PAIRS_TO_TEST:
        print(f"Testing {pair}...", end=" ")
        result = run_single_backtest(pair, days=days)
        if result:
            results.append(result)
            print(f"Trades: {result['trades']} | Win Rate: {result['win_rate']}% | Avg RR: {result['avg_rr']}")
        else:
            print("No trades or data.")

    if results:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        for r in results:
            print(f"{r['pair']}: {r['trades']} trades | {r['win_rate']}% WR | {r['avg_rr']} Avg RR")

if __name__ == "__main__":
    run_full_backtest(days=45)
