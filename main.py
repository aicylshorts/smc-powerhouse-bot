import os
import time
import schedule
import logging
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Load env (for local)
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
OANDA_TOKEN = os.getenv('OANDA_TOKEN')
OANDA_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not all([OANDA_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
    logger.error("Missing required environment variables! Check OANDA_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID")
    exit(1)

logger.info("✅ Environment variables loaded successfully")

from telegram import Bot
from config import ASSETS, TIMEFRAMES, POLL_INTERVAL_SEC, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP
try:
    from utils import calculate_confluence_score, detect_fvg
    from data_fetcher import get_oanda_candles, get_binance_candles
except ImportError as e:
    logger.error(f"Import error: {e}")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)
sent_signals = {}

def is_high_impact_news(symbol):
    # Placeholder - expand later with free news API if needed
    return False

def generate_signals():
    logger.info("Scanning for SMC setups...")
    for broker, symbols in ASSETS.items():
        for sym in symbols:
            for tf in TIMEFRAMES:
                try:
                    if broker == 'OANDA':
                        df = get_oanda_candles(sym, tf)
                    else:
                        df = get_binance_candles(sym, tf)
                    if df.empty:
                        continue
                    # TODO: Full SMC logic - placeholder for now to prevent crash
                    logger.info(f"Fetched data for {sym} {tf} - {len(df)} candles")
                    # For testing, we can send a test message periodically
                except Exception as e:
                    logger.error(f"Error processing {sym} {tf}: {e}")

def daily_summary():
    logger.info("Sending daily summary")
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="Daily SMC Summary (WAT): No signals today or bot is running.")
    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")

# Scheduler
schedule.every(POLL_INTERVAL_SEC).seconds.do(generate_signals)
schedule.every().day.at("23:00").do(daily_summary)  # Midnight WAT approx

if __name__ == "__main__":
    logger.info("🚀 SMC Powerhouse Bot started successfully!")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
