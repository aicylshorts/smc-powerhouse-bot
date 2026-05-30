import os
from dotenv import load_dotenv
load_dotenv()

# Expanded high-liquidity assets for better coverage
ASSETS = {
    'OANDA': [
        # Major Forex
        'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD', 'EUR_JPY', 'GBP_JPY',
        # Metals
        'XAU_USD', 'XAG_USD',
        # Indices
        'NAS100_USD', 'US30_USD', 'SPX500_USD', 'UK100_GBP',
        # Energy
        'NATGAS_USD', 'WTICO_USD'
    ],
    'BINANCE': [
        'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD'
    ]
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 60
COOLDOWN_MIN = 25          # Slightly reduced to catch good setups faster
PROB_THRESHOLD_A = 70
PROB_THRESHOLD_AP = 80
WAT_TZ_OFFSET = 1

# News Filter Settings (expandable)
AVOID_NEWS_MINUTES_BEFORE = 25
AVOID_NEWS_MINUTES_AFTER = 25

# Add more high-impact times as needed (UTC)
HIGH_IMPACT_WINDOWS = [
    (8, 30),   # Example: London open related
    (14, 30),  # NY open / FOMC etc.
    (13, 0),   # Overlap
]

# For Flask
PORT = int(os.getenv('PORT', 10000))
