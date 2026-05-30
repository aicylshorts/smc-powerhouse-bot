import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

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
    all_rrs = []

    pair_stats = defaultdict(lambda: {"traded": 0, "wins": 0, "losses": 0})
    session_stats = defaultdict(lambda: {"traded": 0, "wins": 0, "losses": 0})

    for sig_id, outcome_data in outcomes.items():
        if sig_id not in signals:
            continue

        outcome = outcome_data.get("outcome", "")
        rr = outcome_data.get("rr") or 0

        if outcome != "NO_TRADE":
            total_traded += 1

        sig = signals[sig_id]
        pair = sig.get("symbol", "Unknown")
        session = sig.get("session", "Unknown")

        if outcome == "WIN":
            wins += 1
            win_rrs.append(rr)
            all_rrs.append(rr)
            pair_stats[pair]["wins"] += 1
            session_stats[session]["wins"] += 1
        elif outcome == "LOSS":
            losses += 1
            all_rrs.append(-1)
            pair_stats[pair]["losses"] += 1
            session_stats[session]["losses"] += 1

        if outcome != "NO_TRADE":
            pair_stats[pair]["traded"] += 1
            session_stats[session]["traded"] += 1

    win_rate = round((wins / total_traded * 100), 1) if total_traded > 0 else 0
    avg_win_rr = round(sum(win_rrs) / len(win_rrs), 2) if win_rrs else 0

    # Profit Factor
    gross_profit = sum([r for r in all_rrs if r > 0])
    gross_loss = abs(sum([r for r in all_rrs if r < 0]))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

    # Best performing pairs
    best_pairs = sorted(
        [(p, s["traded"], round(s["wins"]/s["traded"]*100,1)) for p, s in pair_stats.items() if s["traded"] > 0],
        key=lambda x: x[2], reverse=True
    )[:3]

    # Session breakdown
    session_text = "\nSession Performance:\n"
    for session, stats in sorted(session_stats.items()):
        if stats["traded"] > 0:
            wr = round(stats["wins"] / stats["traded"] * 100, 1)
            session_text += f"  {session}: {stats['traded']} trades | {stats['wins']} wins ({wr}%)\n"

    best_pairs_text = "\nTop Performing Pairs:\n"
    for pair, traded, wr in best_pairs:
        best_pairs_text += f"  {pair}: {traded} trades | {wr}% WR\n"

    report = f"""📊 Monthly Performance Report

Total Signals: {total_signals}
Trades Taken: {total_traded}
Skipped (NO_TRADE): {total_signals - total_traded}

Wins: {wins} | Losses: {losses}
Win Rate: {win_rate}%

Average Win RR: {avg_win_rr}R
Profit Factor: {profit_factor}

{best_pairs_text}{session_text}
"""
    return report

def get_recent_performance(days=7):
    data = load_trades()
    outcomes = data.get("outcomes", {})
    signals = data.get("signals", {})

    if not outcomes:
        return "No trades recorded yet."

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    recent = []

    for sig_id, outcome_data in outcomes.items():
        if outcome_data.get("recorded_at", "") >= cutoff:
            recent.append(outcome_data)

    if not recent:
        return f"No trades in the last {days} days."

    wins = sum(1 for o in recent if o.get("outcome") == "WIN")
    total = len(recent)
    wr = round(wins / total * 100, 1)

    return f"Last {days} days: {total} trades | {wins} wins ({wr}% WR)"
