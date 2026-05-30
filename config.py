import os
from dotenv import load_dotenv
load_dotenv()

ASSETS = {
    'OANDA': [
        # Majors
        'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'USD_CHF', 'NZD_USD',
        # EUR Crosses
        'EUR_GBP', 'EUR_JPY', 'EUR_AUD', 'EUR_CAD', 'EUR_NZD', 'EUR_CHF',
        # GBP Crosses
        'GBP_JPY', 'GBP_AUD', 'GBP_CAD', 'GBP_NZD', 'GBP_CHF',
        # AUD / NZD Crosses
        'AUD_JPY', 'AUD_CAD', 'AUD_NZD', 'AUD_CHF',
        'NZD_JPY', 'NZD_CAD', 'NZD_CHF',
        # Other Crosses
        'CAD_JPY', 'CHF_JPY',
        # Metals
        'XAU_USD', 'XAG_USD', 'XPT_USD', 'XPD_USD',
        # Commodities
        'NATGAS_USD', 'WTICO_USD', 'BCO_USD',
        # Indices
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

# For Flask
PORT = int(os.getenv('PORT', 10000))
