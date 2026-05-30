import pandas as pd
from utils import detect_smc_setup
import argparse

def parse_dukascopy_csv(filepath):
    df = pd.read_csv(filepath, header=None)
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y.%m.%d %H:%M:%S')
    df.set_index('datetime', inplace=True)
    df = df[['open', 'high', 'low', 'close']].astype(float)
    return df

def run_csv_backtest(csv_path, pair_name='UNKNOWN', tf='15m'):
    print(f"\n=== Backtesting {pair_name} ({tf}) from CSV ===\n")

    try:
        df = parse_dukascopy_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if len(df) < 100:
        print("Not enough data in CSV.")
        return

    trades = []
    for i in range(60, len(df)):
        window = df.iloc[:i+1]
        setup = detect_smc_setup(window, pair_name, tf)

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
                rr = round((tp2 - entry) / (entry - sl), 2)
            else:
                result = 'LOSS'
                rr = -1.0

            trades.append({'result': result, 'rr': rr})

    if not trades:
        print("No trades generated.")
        return

    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['result'] == 'WIN'])
    total = len(df_trades)
    win_rate = round((wins / total) * 100, 2)
    avg_rr = round(df_trades['rr'].mean(), 2)

    print(f"Total Trades: {total}")
    print(f"Wins: {wins} | Losses: {total - wins}")
    print(f"Win Rate: {win_rate}%")
    print(f"Average RR: {avg_rr}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backtest SMC strategy from Dukascopy CSV')
    parser.add_argument('--csv', type=str, required=True, help='Path to Dukascopy CSV file')
    parser.add_argument('--pair', type=str, default='UNKNOWN', help='Pair name (e.g. XAU_USD)')
    parser.add_argument('--tf', type=str, default='15m', help='Timeframe (15m, 1h, 4h)')

    args = parser.parse_args()
    run_csv_backtest(args.csv, args.pair, args.tf)
