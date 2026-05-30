import os
import time
import schedule
import pandas as pd
from datetime import datetime, timedelta
import telegram
from config import ASSETS, TIMEFRAMES, POLL_INTERVAL_SEC, COOLDOWN_MIN, PROB_THRESHOLD_A, PROB_THRESHOLD_AP

# Telegram bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telegram.Bot(token=TELEGRAM_TOKEN)

sent_signals = {}


def is_high_impact_news(symbol):
    # Placeholder - expand later with free news API
    return False


def generate_signals():
    for broker, symbols in ASSETS.items():
        for sym in symbols:
            for tf in TIMEFRAMES:
                try:
                    if broker == 'OANDA':
                        df = get_oanda_candles(sym, tf)
                    else:
                        df = get_binance_candles(sym, tf)
                    
                    # Basic SMC analysis (will be expanded in utils)
                    score, direction, entry, sl, tp1, tp2 = analyze_smc_setup(df, sym)
                    
                    if score >= PROB_THRESHOLD_A:
                        prob_label = 'A+' if score >= PROB_THRESHOLD_AP else 'A'
                        msg = f"{sym} {direction} @ {entry:.5f} SL:{sl:.5f} TP1:{tp1:.5f} TP2:{tp2:.5f} ({prob_label} {score}%) {tf}\nMonitor CHOCH for exit"
                        
                        key = f"{sym}_{tf}"
                        if not is_high_impact_news(sym) and (key not in sent_signals or time.time() - sent_signals[key] > COOLDOWN_MIN * 60):
                            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
                            sent_signals[key] = time.time()
                except Exception as e:
                    print(f"Error processing {sym} {tf}: {e}")


def daily_summary():
    msg = f"Daily SMC Signals Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')} WAT\nNo new signals today or check logs."
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except:
        pass

# Scheduler
schedule.every(POLL_INTERVAL_SEC).seconds.do(generate_signals)
schedule.every().day.at("23:00").do(daily_summary)  # Midnight WAT approx

if __name__ == "__main__":
    print("SMC Powerhouse Bot started...")
    while True:
        schedule.run_pending()
        time.sleep(30)
