import os
from dotenv import load_dotenv
load_dotenv()

# OANDA temporarily disabled due to network instability on Render free tier.
# Running primarily on Finnhub + yfinance fallback.
ASSETS = {
    'OANDA': [],   # Disabled

    'FINNHUB': [
        'OANDA:EUR_USD', 'OANDA:GBP_USD', 'OANDA:USD_JPY', 'OANDA:AUD_USD',
        'OANDA:XAU_USD', 'OANDA:XAG_USD',
        'OANDA:NAS100_USD', 'OANDA:US30_USD'
    ],

    'BINANCE': [
        'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD'
    ]
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 60
COOLDOWN_MIN = 25
PROB_THRESHOLD_A = 70
PROB_THRESHOLD_AP = 80
WAT_TZ_OFFSET = 1

# News Filter Settings
AVOID_NEWS_MINUTES_BEFORE = 25
AVOID_NEWS_MINUTES_AFTER = 25

HIGH_IMPACT_WINDOWS = [
    (8, 30),
    (14, 30),
    (13, 0),
]

PORT = int(os.getenv('PORT', 10000))
