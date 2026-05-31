import os
import time
import requests
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import investpy
except ImportError:
    investpy = None

def _clean_ohlc(df):
    if df.empty:
        return df
    df = df.dropna()
    df = df[~df.index.duplicated(keep='last')]
    df = df.sort_index()
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
    return df

def _map_oanda_granularity(tf: str) -> str:
    mapping = {
        '15m': 'M15',
        '1h': 'H1',
        '4h': 'H4',
        '1d': 'D',
    }
    return mapping.get(tf, tf)

def _make_request_with_retry(url, headers=None, params=None, max_retries=3, backoff=2):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=12)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(backoff ** attempt)
    return None


def get_fawaz_exchange_rate(base_currency='USD', symbols=None):
    """
    Fawaz - Fine-tuned for SMC
    Spot rates with realistic variation for liquidity & structure detection.
    """
    if symbols is None:
        symbols = ['EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']

    url = f'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base_currency.lower()}.json'

    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        rates = data.get(base_currency.lower(), {})

        if not rates:
            return pd.DataFrame()

        df_data = []
        for sym in symbols:
            rate = rates.get(sym.lower())
            if rate:
                close = float(rate)
                body = close * 0.0002
                wick = close * 0.00035
                df_data.append({
                    'symbol': f'{base_currency}{sym}',
                    'open': round(close - body, 5),
                    'high': round(close + wick, 5),
                    'low': round(close - wick, 5),
                    'close': round(close, 5)
                })

        if not df_data:
            return pd.DataFrame()

        df = pd.DataFrame(df_data)
        df['time'] = pd.Timestamp.now()
        df.set_index('time', inplace=True)
        return _clean_ohlc(df)

    except Exception as e:
        print(f'Fawaz error: {e}')
        return pd.DataFrame()


def get_investpy_data(name, country=None, product_type='indices', interval='Daily'):
    """
    investpy - Fine-tuned + strong fallback for SMC
    """
    if investpy is None:
        print("investpy not installed")
        return pd.DataFrame()

    try:
        if product_type == 'indices':
            df = investpy.get_index_historical_data(
                index=name, country=country or 'united states',
                from_date='01/01/2023', to_date='31/12/2030', interval='Daily'
            )
        elif product_type == 'commodities':
            df = investpy.get_commodity_historical_data(
                commodity=name, from_date='01/01/2023', to_date='31/12/2030', interval='Daily'
            )
        else:
            return pd.DataFrame()

        if df.empty:
            raise ValueError("Empty data from investpy")

        df = df[['Open', 'High', 'Low', 'Close']].copy()
        df.columns = ['open', 'high', 'low', 'close']
        df.index = pd.to_datetime(df.index)
        return _clean_ohlc(df)

    except Exception:
        try:
            if yf:
                ticker_map = {
                    'NAS100': '^NDX', 'US30': '^DJI', 'SPX500': '^GSPC',
                    'Gold': 'GC=F', 'Silver': 'SI=F', 'Crude Oil': 'CL=F'
                }
                ticker = ticker_map.get(name, name)
                df = yf.download(ticker, period='120d', interval='1d', progress=False)
                if not df.empty:
                    df = df[['Open', 'High', 'Low', 'Close']].copy()
                    df.columns = ['open', 'high', 'low', 'close']
                    return _clean_ohlc(df)
        except:
            pass
        return pd.DataFrame()


def get_dukascopy_data(symbol, start_date='2024-01-01', end_date=None, timeframe='H1'):
    """
    Dukascopy Integration (Initial)
    Downloads historical data for backtesting and validation.
    timeframe: 'tick', 'm1', 'm5', 'm15', 'h1', 'd1'
    """
    if end_date is None:
        end_date = pd.Timestamp.now().strftime('%Y-%m-%d')

    print(f"[Dukascopy] Fetching {symbol} {timeframe} from {start_date} to {end_date}...")

    # Placeholder - Full implementation requires dukascopy library or direct download
    # For now we return empty and log. Will be expanded.
    try:
        # Future: Use dukascopy library or direct HTTP download from Dukascopy historical data
        print("[Dukascopy] Full download not yet implemented. Returning empty for now.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Dukascopy error: {e}")
        return pd.DataFrame()


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
        df.set_index('time', inplace=True)
        return _clean_ohlc(df)

    except Exception as e:
        print(f'OANDA error for {instrument} ({granularity}): {e}')
        return pd.DataFrame()


def get_finnhub_candles(symbol, resolution='15', count=300):
    token = os.getenv('FINNHUB_TOKEN')
    if not token:
        print("FINNHUB_TOKEN not set")
        return pd.DataFrame()

    to_time = int(time.time())
    from_time = to_time - (count * 900)

    url = f'https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution={resolution}&from={from_time}&to={to_time}&token={token}'

    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        if data.get('s') != 'ok':
            print(f"Finnhub returned no data for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame({
            'time': pd.to_datetime(data['t'], unit='s'),
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c']
        })
        df.set_index('time', inplace=True)
        return _clean_ohlc(df)

    except Exception as e:
        print(f'Finnhub error for {symbol}: {e}')
        return pd.DataFrame()


def get_twelve_data_candles(symbol, interval='15min', outputsize=300):
    token = os.getenv('TWELVE_DATA_TOKEN')
    if not token:
        print("TWELVE_DATA_TOKEN not set")
        return pd.DataFrame()

    url = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={token}'

    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        if 'values' not in data:
            print(f"Twelve Data error: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()

        df = pd.DataFrame(data['values'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        df = df[['open', 'high', 'low', 'close']].astype(float)
        return _clean_ohlc(df)

    except Exception as e:
        print(f'Twelve Data error for {symbol}: {e}')
        return pd.DataFrame()


def get_alpha_vantage_candles(symbol, interval='15min', outputsize=100):
    api_key = os.getenv('ALPHA_VANTAGE_TOKEN')
    if not api_key:
        print("ALPHA_VANTAGE_TOKEN not set")
        return pd.DataFrame()

    av_interval = {
        '15m': '15min',
        '1h': '60min',
        '4h': '240min'
    }.get(interval, '15min')

    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_FOREX_INTRADAY&from_symbol={symbol.split("/")[0] if "/" in symbol else symbol}&to_symbol={symbol.split("/")[1] if "/" in symbol else "USD"}&interval={av_interval}&outputsize=compact&apikey={api_key}'

    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        key = list(data.keys())[1] if len(data.keys()) > 1 else None
        if not key or 'Time Series' not in str(data.get(key, {})):
            print(f"Alpha Vantage returned no data for {symbol}")
            return pd.DataFrame()

        time_series = data[key]
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.rename(columns={'1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close'})
        df = df[['open', 'high', 'low', 'close']].astype(float)
        df.index = pd.to_datetime(df.index)
        return _clean_ohlc(df)

    except Exception as e:
        print(f'Alpha Vantage error for {symbol}: {e}')
        return pd.DataFrame()


def get_polygon_candles(ticker, multiplier=15, timespan='minute', limit=500):
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("POLYGON_API_KEY not set")
        return pd.DataFrame()

    if timespan == '15m':
        multiplier, timespan = 15, 'minute'
    elif timespan == '1h':
        multiplier, timespan = 60, 'minute'
    elif timespan == '4h':
        multiplier, timespan = 240, 'minute'

    url = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/2020-01-01/now?adjusted=true&sort=desc&limit={limit}&apiKey={api_key}'

    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        if data.get('status') != 'OK' or 'results' not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data['results'])
        df['time'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('time', inplace=True)
        df = df[['o', 'h', 'l', 'c']].copy()
        df.columns = ['open', 'high', 'low', 'close']
        return _clean_ohlc(df)

    except Exception as e:
        print(f'Polygon error for {ticker}: {e}')
        return pd.DataFrame()


def get_yfinance_candles(symbol, period='5d', interval='15m'):
    if yf is None:
        print("yfinance not installed")
        return pd.DataFrame()

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df[['Open', 'High', 'Low', 'Close']].copy()
        df.columns = ['open', 'high', 'low', 'close']
        return _clean_ohlc(df)

    except Exception as e:
        print(f'yfinance error for {symbol}: {e}')
        return pd.DataFrame()


def get_coingecko_candles(coin_id, vs_currency='usd', days=5):
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={vs_currency}&days={days}'

    try:
        resp = _make_request_with_retry(url)
        if resp is None:
            return pd.DataFrame()

        data = resp.json()
        if 'prices' not in data:
            return pd.DataFrame()

        prices = data['prices']
        df = pd.DataFrame(prices, columns=['timestamp', 'close'])
        df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('time', inplace=True)
        df['open'] = df['close']
        df['high'] = df['close']
        df['low'] = df['close']
        return _clean_ohlc(df)

    except Exception as e:
        print(f'CoinGecko error for {coin_id}: {e}')
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
        return _clean_ohlc(df)

    except Exception as e:
        print(f'Binance error for {symbol}: {e}')
        return pd.DataFrame()
