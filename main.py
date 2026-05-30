import os
import time
import threading
import logging
from datetime import datetime
import schedule

from flask import Flask
from dotenv import load_dotenv

# Use the recommended import style for python-telegram-bot v20+
try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:
    import telegram
    Bot = telegram.Bot
    TelegramError = Exception

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Read env vars early
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OANDA_TOKEN = os.getenv('OANDA_TOKEN')

# Basic validation with clear logs
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN is missing! Add it in Render Environment Variables.")
if not TELEGRAM_CHAT_ID:
    logger.error("❌ TELEGRAM_CHAT_ID is missing! Add it in Render Environment Variables (must be numeric chat ID).")

bot = None
chat_id = None

if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        chat_id = TELEGRAM_CHAT_ID.strip() if isinstance(TELEGRAM_CHAT_ID, str) else TELEGRAM_CHAT_ID
        logger.info("✅ Telegram Bot initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Telegram Bot: {e}")
else:
    logger.warning("⚠️ Telegram credentials missing — startup message and signals will be disabled until set.")

sent_signals = {}

@app.route('/')
def home():
    return "SMC Powerhouse Bot is running! ✅"

@app.route('/health')
def health():
    return 'OK', 200

def send_telegram_message(message):
    if bot is None or chat_id is None:
        logger.warning("Telegram not configured — message not sent.")
        return
    try:
        bot.send_message(chat_id=chat_id, text=message)
    except TelegramError as e:
        logger.error(f"❌ Telegram send failed: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error sending Telegram message: {e}")

def is_high_impact_news(symbol):
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
                    if df is None or len(df) < 50:
                        continue
                    setup = detect_smc_setup(df, sym, tf)
                    if setup:
                        score = setup.get('score', 0)
                        if score >= PROB_THRESHOLD_A:
                            direction = setup['direction']
                            entry = setup['entry']
                            sl = setup['sl']
                            tp1 = setup['tp1']
                            tp2 = setup['tp2']
                            prob_label = 'A+' if score >= PROB_THRESHOLD_AP else 'A'
                            msg = f"{sym} {direction} @ {entry:.5f} SL:{sl:.5f} TP1:{tp1:.5f} TP2:{tp2:.5f} ({prob_label} {score}%) {tf}\nMonitor CHOCH for exit"
                            key = f"{sym}_{tf}"
                            if key not in sent_signals or time.time() - sent_signals[key] > COOLDOWN_MIN * 60:
                                send_telegram_message(msg)
                                sent_signals[key] = time.time()
                                logger.info(f"Signal sent: {msg}")
                except Exception as e:
                    logger.error(f"Error processing {sym} {tf}: {e}")

def daily_summary():
    msg = f"Daily SMC Summary (WAT) - {datetime.now().strftime('%Y-%m-%d')}\nNo signals today."
    send_telegram_message(msg)

def run_scheduler():
    schedule.every(POLL_INTERVAL_SEC).seconds.do(generate_signals)
    schedule.every().day.at("23:00").do(daily_summary)
    while True:
        schedule.run_pending()
        time.sleep(30)

def start_bot():
    try:
        if bot and chat_id:
            startup_msg = "🚀 SMC Powerhouse Bot started successfully!\nMonitoring markets for A/A+ setups..."
            send_telegram_message(startup_msg)
            logger.info("✅ Startup message sent to Telegram")
        else:
            logger.warning("⚠️ Skipping startup message — Telegram not configured.")

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("✅ Scheduler started in background thread")
        logger.info("✅ Bot is now running 24/7")
    except Exception as e:
        logger.error(f"Error in start_bot: {e}")

if __name__ == "__main__":
    from config import ASSETS, TIMEFRAMES, POLL_INTERVAL_SEC, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP
    from data_fetcher import get_oanda_candles, get_binance_candles
    from utils import detect_smc_setup

    logger.info("✅ Environment variables loaded successfully")
    start_bot()
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)
