import os
import time
import threading
import logging
from datetime import datetime
import schedule

from flask import Flask
from dotenv import load_dotenv
import telegram

from config import ASSETS, TIMEFRAMES, POLL_INTERVAL_SEC, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP

from data_fetcher import get_oanda_candles, get_binance_candles
from utils import detect_smc_setup

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))
chat_id = os.getenv('TELEGRAM_CHAT_ID')

sent_signals = {}

@app.route('/')
def home():
    return "SMC Powerhouse Bot is running! ✅"

@app.route('/health')
def health():
    return 'OK', 200

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

def is_high_impact_news(symbol):
    # Placeholder - expand with free news API later
    return False

def generate_signals():
    logging.info("Scanning for SMC setups...")
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
                                logging.info(f"Signal sent: {msg}")
                except Exception as e:
                    logging.error(f"Error processing {sym} {tf}: {e}")

def daily_summary():
    msg = f"Daily SMC Summary (WAT) - {datetime.now().strftime('%Y-%m-%d')}\nNo signals today."
    # TODO: improve summary with actual count
    send_telegram_message(msg)

def run_scheduler():
    schedule.every(POLL_INTERVAL_SEC).seconds.do(generate_signals)
    schedule.every().day.at("23:00").do(daily_summary)  # Midnight WAT approx
    while True:
        schedule.run_pending()
        time.sleep(30)

def start_bot():
    try:
        # Send startup message
        startup_msg = "🚀 SMC Powerhouse Bot started successfully!\nMonitoring markets for A/A+ setups..."
        send_telegram_message(startup_msg)
        logging.info("Startup message sent to Telegram")
        
        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logging.info("Scheduler started in background thread")
        
        logging.info("Bot is now running 24/7")
    except Exception as e:
        logging.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    logging.info("✅ Environment variables loaded successfully")
    start_bot()
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)
