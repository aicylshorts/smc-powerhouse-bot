import os
import time
import requests
import pandas as pd

def _map_oanda_granularity(tf: str) -> str:
    mapping = {
        '15m': 'M15',
        '1h': 'H1',
        '4h': 'H4',
        '1d': 'D',
    }
    return mapping.get(tf, tf)

def _make_request_with_retry(url, headers=None, params=None, max_retries=3, backoff=2):
    '''Make HTTP request with retry and exponential backoff'''
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=12)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(backoff ** attempt)  # 2s, 4s, 8s...
    return None

def get_oanda_candles(instrument, granularity='M15', count=300):
    url = f'https://api-fxtrade-practice.oanda.com/v3/instruments/{instrument}/candles'
    headers = {
        'Authorization': f'Bearer {os.getenv("OANDA_TOKEN")}',
        'Content-Type': 'application/json'
    }
    oanda_gran = _map_oanda_granularity(granularity)
    params = {'granularity': oanda_gran, 'count': count}

    try:
        resp = _make_request_with_retry(url, headers=headers, params=params)
        if resp is None:
            return pd.DataFrame()

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
        return df.set_index('time')

    except Exception as e:
        print(f'OANDA error for {instrument} ({granularity}): {e}')
        return pd.DataFrame()


def get_binance_candles(symbol, interval='15m', limit=300):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        if not isinstance(data, list):
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close']].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)
        return df

    except Exception as e:
        print(f'Binance error for {symbol}: {e}')
        return pd.DataFrame()
