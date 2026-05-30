# SMC Powerhouse Bot

Mulham Trading refined Smart Money Concepts (SMC) signal generator.

## Features
- Live A/A+ SMC setups (Liquidity Sweep + FVG + OB + BOS)
- OANDA for Forex, Metals, Indices (EUR_USD, XAU_USD, US30, NAS100_USD etc.)
- Binance for Crypto (BTCUSD, ETHUSD, SOLUSD)
- Telegram alerts
- Dynamic TP based on probability
- Daily summary at midnight WAT (UTC+1)
- High impact news filter (placeholder)
- Multi-timeframe confluence

## Setup
1. Copy .env.example to .env and fill credentials
2. `pip install -r requirements.txt`
3. `python main.py`

Deploy on Render.com as Python Worker.

Assets defined in config.py