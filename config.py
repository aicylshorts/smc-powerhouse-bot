import os
from dotenv import load_dotenv
load_dotenv()

# Data sources with OANDA brought back (small list to avoid previous issues)
ASSETS = {
    'OANDA': [
        'XAU_USD', 'XAG_USD', 'EUR_USD', 'GBP_USD'
    ],

    'FINNHUB': [
        'OANDA:EUR_USD', 'OANDA:GBP_USD', 'OANDA:USD_JPY',
        'OANDA:XAU_USD', 'OANDA:XAG_USD',
        'OANDA:NAS100_USD'
    ],

    'TWELVE_DATA': [
        'EUR/USD', 'GBP/USD', 'USD/JPY',
        'XAU/USD', 'XAG/USD',
        'NAS100/USD'
    ],

    'POLYGON': [
        'C:EURUSD', 'C:GBPUSD', 'C:USDJPY',
        'X:XAUUSD', 'X:XAGUSD',
        'I:SPX'
    ],

    'BINANCE': [
        'BTCUSD', 'ETHUSD', 'SOLUSD'
    ]
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 90
COOLDOWN_MIN = 30
PROB_THRESHOLD_A = 70
PROB_THRESHOLD_AP = 80
WAT_TZ_OFFSET = 1

AVOID_NEWS_MINUTES_BEFORE = 25
AVOID_NEWS_MINUTES_AFTER = 25

HIGH_IMPACT_WINDOWS = [
    (8, 30),
    (14, 30),
    (13, 0),
]

PORT = int(os.getenv('PORT', 10000))
