import os
from dotenv import load_dotenv
load_dotenv()

ASSETS = {
    'OANDA': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'XAG_USD', 'US30_USD', 'NAS100_USD'],
    'BINANCE': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 180   # Every 3 minutes to be gentle
COOLDOWN_MIN = 30
PROB_THRESHOLD_A = 70
PROB_THRESHOLD_AP = 80

WAT_TZ_OFFSET = 1
