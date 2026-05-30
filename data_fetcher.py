import requests
import pandas as pd
import os
from datetime import datetime

def get_oanda_candles(instrument, granularity='M15', count=500):
    '''Fetch candles from OANDA'''
    token = os.getenv('OANDA_TOKEN')
    account_id = os.getenv('OANDA_ACCOUNT_ID')  # not always needed for public data
    url = f'https://api-fxtrade.oanda.com/v3/instruments/{instrument}/candles'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {
        'granularity': granularity,
        'count': count
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()['candles']
        
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

def get_binance_candles(symbol, interval='15m', limit=500):
    '''Fetch candles from Binance public API'''
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'trades', 'taker_base', 'taker_quote', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close']].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df = df.astype(float)
        return df
    except Exception as e:
        print(f'Binance error for {symbol}: {e}')
        return pd.DataFrame()
