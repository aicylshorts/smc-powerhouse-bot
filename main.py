import os
import time
import threading
import logging
from datetime import datetime, timezone
import schedule
import requests

import tracker

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
    logger.info('Scanning for SMC setups...')
    check_telegram_commands()

    from config import ASSETS, TIMEFRAMES, POLL_INTERVAL_SEC, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP
    from data_fetcher import get_oanda_candles, get_binance_candles
    from utils import detect_smc_setup

    current_session = get_trading_session()

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
                            tp3 = setup['tp3']
                            tp1_r = setup.get('tp1_r', 1.5)
                            tp2_r = setup.get('tp2_r', 2.8)
                            tp3_r = setup.get('tp3_r', 4.0)
                            prob_label = 'A+' if score >= PROB_THRESHOLD_AP else 'A'

                            short_sym = sym.replace('_', '')[:6]
                            signal_id = f'{short_sym}{int(time.time()) % 10000}'

                            tracker.log_signal(signal_id, sym, direction, entry, sl, tp1, tp2, tp3, score, tf, current_session)

                            msg = (f'{sym} {direction} @ {entry:.5f}\n'
                                   f'SL: {sl:.5f}\n'
                                   f'TP1: {tp1_r}R ({tp1:.5f})\n'
                                   f'TP2: {tp2_r}R ({tp2:.5f})\n'
                                   f'TP3: {tp3_r}R ({tp3:.5f})\n'
                                   f'Session: {current_session}\n'
                                   f'({prob_label} {score}%) {tf}\n'
                                   f'#{signal_id}\n'
                                   f'Monitor CHOCH for exit')

                            key = f'{sym}_{tf}'
                            if key not in sent_signals or time.time() - sent_signals[key] > COOLDOWN_MIN * 60:
                                send_telegram_message(msg)
                                sent_signals[key] = time.time()
                                logger.info(f'Signal sent: #{signal_id}')
                except Exception as e:
                    logger.error(f'Error processing {sym} {tf}: {e}')

def send_monthly_report():
    report = tracker.get_monthly_report()
    send_telegram_message('📊 Monthly Performance Report\n' + report)

def run_scheduler():
    schedule.every(60).seconds.do(generate_signals)
    schedule.every().day.at('00:05').do(send_monthly_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

def start_bot():
    try:
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            startup_msg = '🚀 SMC Powerhouse Bot started successfully!\nMonitoring markets for A/A+ setups...'
            send_telegram_message(startup_msg)

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info('Scheduler started')
        logger.info('Bot running 24/7')
    except Exception as e:
        logger.error(f'start_bot error: {e}')

if __name__ == '__main__':
    logger.info('Starting SMC Powerhouse Bot...')
    start_bot()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
