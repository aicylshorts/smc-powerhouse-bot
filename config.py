import os
from dotenv import load_dotenv
load_dotenv()

ASSETS = {
    'OANDA': [
        'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'USD_CHF', 'NZD_USD',
        'EUR_GBP', 'EUR_JPY', 'EUR_AUD', 'EUR_CAD', 'EUR_NZD', 'EUR_CHF',
        'GBP_JPY', 'GBP_AUD', 'GBP_CAD', 'GBP_NZD', 'GBP_CHF',
        'AUD_JPY', 'AUD_CAD', 'AUD_NZD', 'AUD_CHF',
        'NZD_JPY', 'NZD_CAD', 'NZD_CHF',
        'CAD_JPY', 'CHF_JPY',
        'XAU_USD', 'XAG_USD', 'XPT_USD', 'XPD_USD',
        'NATGAS_USD', 'WTICO_USD', 'BCO_USD',
        'US30_USD', 'NAS100_USD', 'SPX500_USD', 'UK100_GBP', 'DE30_EUR', 'FR40_EUR', 'JP225_USD'
    ],
    'BINANCE': ['BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'ADAUSD']
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 60
COOLDOWN_MIN = 30
PROB_THRESHOLD_A = 70
PROB_THRESHOLD_AP = 80
WAT_TZ_OFFSET = 1

# News Filter Settings
AVOID_NEWS_MINUTES_BEFORE = 30
AVOID_NEWS_MINUTES_AFTER = 30

# Simple high-impact time windows (UTC hour, minute)
# You can add more times here
HIGH_IMPACT_WINDOWS = [
    (14, 30),   # US data example
]

# For Flask
PORT = int(os.getenv('PORT', 10000))
