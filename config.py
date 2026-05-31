import os
from dotenv import load_dotenv
load_dotenv()

# Dominant sources: Fawaz (Forex + Crypto) + investpy (Indices + Commodities)
ASSETS = {
    'FAWAZ_EXCHANGE': [
        'USD'   # Handles EURUSD, GBPUSD, USDJPY, BTC, ETH, SOL, XRP
    ],

    'INVESTPY': [
        'NAS100', 'US30', 'SPX500',      # Indices
        'Gold', 'Silver', 'Crude Oil'   # Commodities
    ],

    # Fallback sources (only used if primary fails)
    'OANDA': [
        'XAU_USD', 'XAG_USD', 'EUR_USD', 'GBP_USD'
    ],

    'ALPHA_VANTAGE': [
        'EUR/USD', 'GBP/USD', 'XAU/USD'
    ],

    'POLYGON': [
        'C:EURUSD', 'C:GBPUSD', 'C:USDJPY',
        'X:XAUUSD', 'X:XAGUSD'
    ],

    'BINANCE': [
        'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD'
    ]
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 120
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
