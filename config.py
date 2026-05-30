import os
from dotenv import load_dotenv
load_dotenv()

ASSETS = {
    'OANDA': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD', 'XAG_USD', 'US30_USD', 'NAS100_USD'],
    'BINANCE': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
}

TIMEFRAMES = ['15m', '1h', '4h']  # HTF bias + LTF entry
POLL_INTERVAL_SEC = 300  # 5 min
COOLDOWN_MIN = 45
PROB_A_MIN = 70
PROB_AP_MIN = 80
WAT_TIMEZONE = 'Africa/Lagos'  # UTC+1
DAILY_SUMMARY_HOUR = 23  # 11 PM WAT

# OANDA granularity mapping
GRANULARITY_MAP = {
    '15m': 'M15',
    '1h': 'H1',
    '4h': 'H4'
}

print('Config loaded. Assets:', list(ASSETS['OANDA']) + [s.replace('USDT','USD') for s in ASSETS['BINANCE']])