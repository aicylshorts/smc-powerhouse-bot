import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from utils import detect_smc_setup

load_dotenv()

OANDA_TOKEN = os.getenv('OANDA_TOKEN')

# Expanded test list
PAIRS_TO_TEST = [
    'XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD',
    'NAS100_USD', 'US30_USD'
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
    if df.empty or len(df) < 80:
        return None

    trades = []
    for i in range(60, len(df)):
        window = df.iloc[:i+1]
        setup = detect_smc_setup(window, instrument, granularity)

        if setup:
            direction = setup['direction']
            entry = setup['entry']
            sl = setup['sl']
            tp2 = setup['tp2']
            tp3 = setup.get('tp3', tp2)

            future = df.iloc[i+1:]

            if direction == 'BUY':
                hit_tp2 = future[future['high'] >= tp2]
                hit_tp3 = future[future['high'] >= tp3]
                hit_sl = future[future['low'] <= sl]
            else:
                hit_tp2 = future[future['low'] <= tp2]
                hit_tp3 = future[future['low'] <= tp3]
                hit_sl = future[future['high'] >= sl]

            if not hit_tp2.empty and (hit_sl.empty or hit_tp2.index[0] < hit_sl.index[0]):
                result = 'WIN'
                rr = round((tp2 - entry) / (entry - sl), 2)
            else:
                result = 'LOSS'
                rr = -1.0

            trades.append({'result': result, 'rr': rr})

    if not trades:
        return None

    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['result'] == 'WIN'])
    total = len(df_trades)
    win_rate = round((wins / total) * 100, 2)

    # Profit Factor
    gross_profit = df_trades[df_trades['rr'] > 0]['rr'].sum()
    gross_loss = abs(df_trades[df_trades['rr'] < 0]['rr'].sum())
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

    return {
        'pair': instrument,
        'trades': total,
        'wins': wins,
        'win_rate': win_rate,
        'profit_factor': profit_factor
    }


def run_full_backtest(days=30):
    print(f"\n{'='*65}")
    print(f"SMC POWERHOUSE BACKTEST - Last {days} days (Improved Engine)")
    print(f"{'='*65}\n")

    results = []
    for pair in PAIRS_TO_TEST:
        print(f"Testing {pair}...", end=" ")
        result = run_single_backtest(pair, days=days)
        if result:
            results.append(result)
            print(f"Trades: {result['trades']} | WR: {result['win_rate']}% | PF: {result['profit_factor']}")
        else:
            print("No trades or insufficient data.")

    if results:
        print(f"\n{'='*65}")
        print("SUMMARY")
        print(f"{'='*65}")
        for r in results:
            print(f"{r['pair']}: {r['trades']} trades | {r['win_rate']}% WR | PF: {r['profit_factor']}")

        avg_wr = round(sum(r['win_rate'] for r in results) / len(results), 2)
        print(f"\nAverage Win Rate across pairs: {avg_wr}%")

if __name__ == "__main__":
    run_full_backtest(days=45)
