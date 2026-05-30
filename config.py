import os
from dotenv import load_dotenv
load_dotenv()

ASSETS = {
    'OANDA': [
        'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'USD_CHF', 'NZD_USD',
        'EUR_GBP', 'EUR_JPY', 'GBP_JPY', 'AUD_JPY', 'XAU_USD', 'XAG_USD',
        'NATGAS_USD', 'USOIL', 'UKOIL',
        'US30_USD', 'NAS100_USD', 'DE30_EUR', 'UK100_GBP'
    ],
    'BINANCE': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 60
COOLDOWN_MIN = 30
PROB_THRESHOLD_A = 70
PROB_THRESHOLD_AP = 80
WAT_TZ_OFFSET = 1

# For Flask
PORT = int(os.getenv('PORT', 10000))
