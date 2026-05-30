import os
import requests
import pandas as pd
from datetime import datetime

def get_oanda_candles(instrument, granularity='M15', count=300):
    url = f'https://api-fxtrade.oanda.com/v3/instruments/{instrument}/candles'
    headers = {
        'Authorization': f'Bearer {os.getenv("OANDA_TOKEN")}',
        'Content-Type': 'application/json'
    }
    params = {'granularity': granularity, 'count': count}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()['candles']
        df = pd.DataFrame([{
            'time': pd.to_datetime(c['time']),
            'open': float(c['mid']['o']),
            'high': float(c['mid']['h']),
            'low': float(c['mid']['l']),
            'close': float(c['mid']['c'])
        } for c in data])
        return df.set_index('time')
    except Exception as e:
        print(f'OANDA error for {instrument}: {e}')
        return pd.DataFrame()

def get_binance_candles(symbol, interval='15m', limit=300):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close']].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)
        return df
    except Exception as e:
        print(f'Binance error for {symbol}: {e}')
        return pd.DataFrame()
