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
    total_traded = 0
    wins = 0
    losses = 0
    win_rrs = []

    # Session stats
    session_stats = {}

    for sig_id, outcome_data in outcomes.items():
        if sig_id not in signals:
            continue

        outcome = outcome_data.get("outcome", "")
        rr = outcome_data.get("rr")

        if outcome != "NO_TRADE":
            total_traded += 1

        if outcome == "WIN":
            wins += 1
            if rr:
                win_rrs.append(rr)
        elif outcome == "LOSS":
            losses += 1

        # Session breakdown
        session = signals[sig_id].get("session", "Unknown")
        if session not in session_stats:
            session_stats[session] = {"traded": 0, "wins": 0, "losses": 0}

        if outcome != "NO_TRADE":
            session_stats[session]["traded"] += 1
        if outcome == "WIN":
            session_stats[session]["wins"] += 1
        if outcome == "LOSS":
            session_stats[session]["losses"] += 1

    win_rate = round((wins / total_traded * 100), 1) if total_traded > 0 else 0
    avg_rr = round(sum(win_rrs) / len(win_rrs), 2) if win_rrs else 0

    # Build session breakdown text
    session_text = "\nSession Breakdown:\n"
    for session, stats in session_stats.items():
        s_traded = stats["traded"]
        s_wins = stats["wins"]
        s_wr = round((s_wins / s_traded * 100), 1) if s_traded > 0 else 0
        session_text += f"- {session}: {s_traded} trades | {s_wins} wins ({s_wr}%)\n"

    report = f"""Monthly Performance Report

Total Signals Sent: {total_signals}
Trades Taken: {total_traded}
Skipped (NO TRADE): {total_signals - total_traded}

Wins: {wins}
Losses: {losses}
Win Rate: {win_rate}%

Average RR (on wins): {avg_rr}R
{session_text}
"""
    return report
