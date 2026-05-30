import json
import os
from datetime import datetime

TRADES_FILE = "trades.json"


def load_trades():
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    return {"signals": {}, "outcomes": {}}


def save_trades(data):
    with open(TRADES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_signal(signal_id, symbol, direction, entry, sl, tp1, tp2, tp3, score, tf, session="Unknown", timestamp=None):
    data = load_trades()
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    data["signals"][signal_id] = {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "score": score,
        "tf": tf,
        "session": session,
        "timestamp": timestamp
    }
    save_trades(data)


def record_outcome(signal_id, outcome, rr=None):
    data = load_trades()
    if signal_id not in data["signals"]:
        return False, "Signal ID not found"

    data["outcomes"][signal_id] = {
        "outcome": outcome.upper(),
        "rr": rr,
        "recorded_at": datetime.now().isoformat()
    }
    save_trades(data)
    return True, "Recorded"


def get_monthly_report(year=None, month=None):
    data = load_trades()
    if not data["signals"]:
        return "No signals recorded yet."

    signals = data["signals"]
    outcomes = data["outcomes"]

    total_signals = len(signals)
    total_traded = len([o for o in outcomes.values() if o["outcome"] != "NO_TRADE"])
    wins = len([o for o in outcomes.values() if o["outcome"] == "WIN"])
    losses = len([o for o in outcomes.values() if o["outcome"] == "LOSS"])

    win_rate = round((wins / total_traded * 100), 1) if total_traded > 0 else 0

    win_rrs = [o["rr"] for o in outcomes.values() if o["outcome"] == "WIN" and o.get("rr")]
    avg_rr = round(sum(win_rrs) / len(win_rrs), 2) if win_rrs else 0

    report = f"""Monthly Performance Report

Total Signals Sent: {total_signals}
Trades Taken: {total_traded}
Skipped (NO TRADE): {total_signals - total_traded}

Wins: {wins}
Losses: {losses}
Win Rate: {win_rate}%

Average RR (on wins): {avg_rr}R
"""
    return report
