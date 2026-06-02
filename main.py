import os
import time
import threading
import logging
from datetime import datetime, timezone
import schedule
import requests
from dotenv import load_dotenv
from flask import Flask

import tracker
from utils import detect_smc_setup

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error('Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID!')
else:
    logger.info('Telegram credentials loaded')

sent_signals = {}
last_update_id = 0

def self_ping():
    port = os.environ.get('PORT', '10000')
    url = f'http://127.0.0.1:{port}/health'
    while True:
        try:
            requests.get(url, timeout=5)
        except:
            pass
        time.sleep(280)

def get_trading_session():
    hour = datetime.now(timezone.utc).hour
    if 0 <= hour < 8:
        return 'Asian'
    elif 8 <= hour < 13:
        return 'London'
    elif 13 <= hour < 17:
        return 'London-NY Overlap'
    elif 17 <= hour < 22:
        return 'New York'
    else:
        return 'Late NY / Asian'

def calculate_position_size(entry, sl, risk_usd=10):
    risk_per_unit = abs(entry - sl)
    if risk_per_unit == 0:
        return 0.01
    size = risk_usd / risk_per_unit
    return max(round(size, 2), 0.01)

def is_high_impact_news_time(symbol=None):
    from config import AVOID_NEWS_MINUTES_BEFORE, AVOID_NEWS_MINUTES_AFTER, HIGH_IMPACT_WINDOWS
    now = datetime.now(timezone.utc)
    sensitivity = 1.3 if symbol and any(x in symbol for x in ['XAU', 'XAG', 'NAS', 'US30']) else 1.0
    adjusted_before = int(AVOID_NEWS_MINUTES_BEFORE * sensitivity)
    adjusted_after = int(AVOID_NEWS_MINUTES_AFTER * sensitivity)

    for news_hour, news_minute in HIGH_IMPACT_WINDOWS:
        news_time = now.replace(hour=news_hour, minute=news_minute, second=0, microsecond=0)
        time_diff = (now - news_time).total_seconds() / 60
        if -adjusted_before <= time_diff <= adjusted_after:
            return True
    return False

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f'Telegram send error: {e}')

def check_telegram_commands():
    global last_update_id
    if not TELEGRAM_TOKEN:
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5'
    try:
        resp = requests.get(url, timeout=10).json()
        for update in resp.get('result', []):
            last_update_id = update['update_id']
            message = update.get('message', {})
            text = message.get('text', '')
            if text.startswith('/'):
                handle_command(text)
    except:
        pass

def handle_command(text):
    parts = text.strip().split()
    cmd = parts[0].lower()

    if cmd == '/stats':
        report = tracker.get_monthly_report()
        send_telegram_message(report)
        return

    if len(parts) < 2:
        return
    signal_id = parts[1].replace('#', '')

    if cmd == '/win' and len(parts) >= 3:
        try:
            rr = float(parts[2].replace('R', ''))
        except:
            rr = None
        tracker.record_outcome(signal_id, 'WIN', rr)
        send_telegram_message(f'Recorded WIN for #{signal_id}')

    elif cmd == '/loss':
        tracker.record_outcome(signal_id, 'LOSS')
        send_telegram_message(f'Recorded LOSS for #{signal_id}')

    elif cmd == '/be':
        tracker.record_outcome(signal_id, 'BE')
        send_telegram_message(f'Recorded Breakeven for #{signal_id}')

    elif cmd == '/notrade':
        tracker.record_outcome(signal_id, 'NO_TRADE')
        send_telegram_message(f'Marked as NO TRADE for #{signal_id}')

@app.route('/')
def home():
    return 'SMC Powerhouse Bot is running!'

@app.route('/health')
def health():
    return 'OK', 200

def generate_signals():
    logger.info('Scanning for high-quality SMC setups...')
    check_telegram_commands()

    from config import ASSETS, TIMEFRAMES, COOLDOWN_MIN, PROB_THRESHOLD_A
    from data_fetcher import (
        get_fawaz_exchange_rate, get_investpy_data, get_dukascopy_data
    )

    current_session = get_trading_session()

    for broker, symbols in ASSETS.items():
        for sym in symbols:
            if is_high_impact_news_time(symbol=sym):
                continue

            htf_df = None
            try:
                if broker == 'INVESTPY':
                    htf_df = get_investpy_data(sym, product_type='commodities' if 'Gold' in sym or 'Silver' in sym else 'indices')
                elif broker == 'FAWAZ_EXCHANGE':
                    htf_df = get_fawaz_exchange_rate()
            except:
                pass

            for tf in TIMEFRAMES:
                df = None

                if broker == 'FAWAZ_EXCHANGE':
                    df = get_fawaz_exchange_rate()
                elif broker == 'INVESTPY':
                    product = 'commodities' if 'Gold' in sym or 'Silver' in sym else 'indices'
                    df = get_investpy_data(sym, product_type=product)

                if df is None or len(df) < 50:
                    continue

                setup = detect_smc_setup(df, sym, tf, htf_df=htf_df)

                if setup and setup.get('score', 0) >= PROB_THRESHOLD_A:
                    direction = setup['direction']
                    entry = setup['entry']
                    sl = setup['sl']
                    tp1 = setup['tp1']
                    tp2 = setup['tp2']
                    tp3 = setup['tp3']
                    score = setup['score']

                    risk_usd = 10  # User can change this
                    position_size = calculate_position_size(entry, sl, risk_usd)

                    short_sym = sym.replace('_', '')[:8]
                    signal_id = f'{short_sym}{int(time.time()) % 10000}'

                    tracker.log_signal(signal_id, sym, direction, entry, sl, tp1, tp2, tp3, score, tf, current_session)

                    msg = (f'{sym} {direction} @{entry}\n'
                           f'SL: {sl} | Size: {position_size} lots (~${risk_usd} risk)\n'
                           f'TP1: {tp1} ({setup.get("tp1_r", 1.5)}R) | TP2: {tp2} ({setup.get("tp2_r", 2.8)}R) | TP3: {tp3} ({setup.get("tp3_r", 4.5)}R)\n'
                           f'Score: {score}% | {tf} | {current_session}\n'
                           f'#{signal_id}\nMonitor CHOCH for exit')

                    key = f'{sym}_{tf}'
                    if key not in sent_signals or time.time() - sent_signals[key] > COOLDOWN_MIN * 60:
                        send_telegram_message(msg)
                        sent_signals[key] = time.time()
                        logger.info(f'High-quality signal sent: #{signal_id} | Score: {score}')


def send_daily_report():
    report = tracker.get_monthly_report()
    send_telegram_message('Daily Performance Summary\n' + report)

def run_scheduler():
    schedule.every(60).seconds.do(generate_signals)
    schedule.every().day.at('00:05').do(send_daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

def start_bot():
    try:
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            startup_msg = 'SMC Powerhouse Bot started successfully!\nMonitoring for high-quality A/A+ SMC setups...'
            send_telegram_message(startup_msg)

        ping_thread = threading.Thread(target=self_ping, daemon=True)
        ping_thread.start()

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info('Bot running 24/7')
    except Exception as e:
        logger.error(f'start_bot error: {e}')

if __name__ == '__main__':
    logger.info('Starting SMC Powerhouse Bot...')
    start_bot()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
