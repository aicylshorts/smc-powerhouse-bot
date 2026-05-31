import os
from dotenv import load_dotenv
load_dotenv()

# Priority: Finnhub (1) -> Twelve Data (2) -> Polygon (3) -> yfinance (Fallback)
ASSETS = {
    'OANDA': [],

    'FINNHUB': [
        'OANDA:EUR_USD', 'OANDA:GBP_USD', 'OANDA:USD_JPY', 'OANDA:AUD_USD', 'OANDA:USD_CAD',
        'OANDA:XAU_USD', 'OANDA:XAG_USD',
        'OANDA:NAS100_USD', 'OANDA:US30_USD', 'OANDA:SPX500_USD'
    ],

    'TWELVE_DATA': [
        'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'NZD/USD',
        'XAU/USD', 'XAG/USD',
        'NAS100/USD', 'US30/USD', 'SPX500/USD'
    ],

    'POLYGON': [
        'C:EURUSD', 'C:GBPUSD', 'C:USDJPY', 'C:AUDUSD', 'C:USDCAD',
        'X:XAUUSD', 'X:XAGUSD',
        'I:SPX', 'I:NDX', 'I:DJI'
    ],

    'BINANCE': [
        'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'ADAUSD'
    ]
}

TIMEFRAMES = ['15m', '1h', '4h']
POLL_INTERVAL_SEC = 60
COOLDOWN_MIN = 25
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
