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

def calculate_risk_per_lot(sl_price, entry_price, symbol):
    sl_distance = abs(sl_price - entry_price)
    if 'XAU' in symbol or 'XAG' in symbol:
        risk_per_0_01 = round(sl_distance * 10, 2)
    else:
        risk_per_0_01 = round(sl_distance * 10, 2)
    return risk_per_0_01

def is_high_impact_news_time():
    from config import AVOID_NEWS_MINUTES_BEFORE, AVOID_NEWS_MINUTES_AFTER, HIGH_IMPACT_WINDOWS
    now = datetime.now(timezone.utc)
    for news_hour, news_minute in HIGH_IMPACT_WINDOWS:
        news_time = now.replace(hour=news_hour, minute=news_minute, second=0, microsecond=0)
        time_diff = (now - news_time).total_seconds() / 60
        if -AVOID_NEWS_MINUTES_BEFORE <= time_diff <= AVOID_NEWS_MINUTES_AFTER:
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

    from config import ASSETS, TIMEFRAMES, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP
    from data_fetcher import (
        get_binance_candles, get_finnhub_candles, get_twelve_data_candles,
        get_alpha_vantage_candles, get_tiingo_candles, get_polygon_candles,
        get_oanda_candles, get_yfinance_candles
    )
    from utils import detect_smc_setup

    current_session = get_trading_session()
    high_news = is_high_impact_news_time()

    if high_news:
        logger.info('High impact news window active - skipping scan')
        return

    for broker, symbols in ASSETS.items():
        for sym in symbols:
            for tf in TIMEFRAMES:
                try:
                    df = None
                    htf_df = None

                    if broker == 'FINNHUB':
                        finnhub_res = '15' if tf == '15m' else ('60' if tf == '1h' else '240')
                        df = get_finnhub_candles(sym, resolution=finnhub_res)

                        if df is None or len(df) < 50:
                            df = get_twelve_data_candles(sym.split(':')[-1], interval=tf)

                        if df is None or len(df) < 50:
                            df = get_alpha_vantage_candles(sym.split(':')[-1], interval=tf)

                        if df is None or len(df) < 50:
                            df = get_tiingo_candles(sym.split(':')[-1].lower(), resampleFreq='1hour' if tf == '1h' else '15min')

                        if df is None or len(df) < 50:
                            yf_symbol = sym.split(':')[-1].replace('_', '') + '=X'
                            df = get_yfinance_candles(yf_symbol, interval=tf)

                    elif broker == 'OANDA':
                        df = get_oanda_candles(sym, tf)

                    elif broker == 'TWELVE_DATA':
                        df = get_twelve_data_candles(sym, interval=tf)

                    elif broker == 'ALPHA_VANTAGE':
                        df = get_alpha_vantage_candles(sym, interval=tf)

                    elif broker == 'TIINGO':
                        df = get_tiingo_candles(sym, resampleFreq='1hour' if tf == '1h' else '15min')

                    elif broker == 'POLYGON':
                        df = get_polygon_candles(sym, timespan=tf)

                    elif broker == 'BINANCE':
                        df = get_binance_candles(sym, tf)

                    if df is None or len(df) < 50:
                        continue

                    setup = detect_smc_setup(df, sym, tf, htf_df=htf_df)
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

                            short_sym = sym.replace('_', '')[:8]
                            signal_id = f'{short_sym}{int(time.time()) % 10000}'

                            risk_per_lot = calculate_risk_per_lot(sl, entry, sym)

                            tracker.log_signal(signal_id, sym, direction, entry, sl, tp1, tp2, tp3, score, tf, current_session)

                            msg = (f'{sym} {direction} @{entry:.5f}\n'
                                   f'SL: {sl:.5f} | Risk/0.01lot ~${risk_per_lot}\n'
                                   f'TP1: {tp1_r}R ({tp1:.5f}) | TP2: {tp2_r}R ({tp2:.5f}) | TP3: {tp3_r}R ({tp3:.5f})\n'
                                   f'Session: {current_session} | ({prob_label} {score}%) {tf}\n'
                                   f'#{signal_id}\nMonitor CHOCH for exit')

                            key = f'{sym}_{tf}'
                            if key not in sent_signals or time.time() - sent_signals[key] > COOLDOWN_MIN * 60:
                                send_telegram_message(msg)
                                sent_signals[key] = time.time()
                                logger.info(f'High-quality signal sent: #{signal_id} | Score: {score}')

                except Exception as e:
                    logger.error(f'Error processing {sym} {tf}: {e}')

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
        logger.info('Self-ping started (keeps instance awake)')

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
