import os
import time
import threading
import logging
from datetime import datetime
import schedule
import requests

from flask import Flask
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("❌ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID in Render Environment Variables!")
else:
    logger.info("✅ Telegram credentials loaded")

sent_signals = {}

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("✅ Telegram message sent successfully")
        else:
            logger.error(f"❌ Telegram API error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram message: {e}")

@app.route('/')
def home():
    return "SMC Powerhouse Bot is running! ✅"

@app.route('/health')
def health():
    return 'OK', 200

def generate_signals():
    logger.info("Scanning for SMC setups...")
    from config import ASSETS, TIMEFRAMES, POLL_INTERVAL_SEC, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP
    from data_fetcher import get_oanda_candles, get_binance_candles
    from utils import detect_smc_setup

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
                            tp1_r = setup.get('tp1_r', 1.6)
                            tp2_r = setup.get('tp2_r', 3.0)
                            prob_label = 'A+' if score >= PROB_THRESHOLD_AP else 'A'

                            # Build message with RR + actual prices
                            msg = f"{sym} {direction} @ {entry:.5f}\nSL: {sl:.5f}\nTP1: {tp1_r}R ({tp1:.5f})\nTP2: {tp2_r}R ({tp2:.5f})"

                            if 'tp3' in setup:
                                tp3 = setup['tp3']
                                tp3_r = setup.get('tp3_r', 4.8)
                                msg += f"\nTP3: {tp3_r}R ({tp3:.5f})"

                            msg += f"\n({prob_label} {score}%) {tf}\nMonitor CHOCH for exit"

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
    schedule.every(60).seconds.do(generate_signals)
    schedule.every().day.at("23:00").do(daily_summary)
    while True:
        schedule.run_pending()
        time.sleep(30)

def start_bot():
    try:
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            startup_msg = "🚀 SMC Powerhouse Bot started successfully!\nMonitoring markets for A/A+ setups..."
            send_telegram_message(startup_msg)
        else:
            logger.warning("Skipping Telegram startup message (credentials missing)")

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("✅ Scheduler started")
        logger.info("✅ Bot running 24/7")
    except Exception as e:
        logger.error(f"start_bot error: {e}")

if __name__ == "__main__":
    logger.info("✅ Starting SMC Powerhouse Bot...")
    start_bot()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
