import os
from dotenv import load_dotenv
load_dotenv()

ASSETS = {
    'OANDA': [
        # Core pairs only (reduced to minimize errors)
        'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD',
        'XAU_USD', 'XAG_USD',
        'NAS100_USD', 'US30_USD'
    ],
    'BINANCE': [
        'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'ADAUSD', 'BNBUSD'
    ],
    'FINNHUB': [
        'OANDA:EUR_USD', 'OANDA:GBP_USD', 'OANDA:USD_JPY',
        'OANDA:XAU_USD'
    ]
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

HIGH_IMPACT_WINDOWS = [
    (14, 30),
]

# For Flask
PORT = int(os.getenv('PORT', 10000))
