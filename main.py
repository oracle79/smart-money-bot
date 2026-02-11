import requests
import time
from collections import defaultdict
from datetime import datetime, timedelta
import math
import os

# ==============================
# CONFIG
# ==============================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MIN_TRADE_SIZE = 2000
CLUSTER_THRESHOLD = 3
TIME_WINDOW_MINUTES = 10

SMART_WALLETS = {
    "0x111",
    "0x222",
    "0x333",
}

WALLET_SCORES = {
    "0x111": 90,
    "0x222": 80,
    "0x333": 85,
}

recent_trades = defaultdict(list)

# ==============================
# TELEGRAM ALERT
# ==============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# ==============================
# CLUSTER LOGIC
# ==============================

def compute_cluster_score(trades):
    total_score = 0
    total_size = 0

    for trade in trades:
        wallet = trade["wallet"]
        size = trade["size"]
        wallet_score = WALLET_SCORES.get(wallet, 50)

        influence = wallet_score * math.log(size + 1)
        total_score += influence
        total_size += size

    score = min(int(total_score / 100), 100)
    return score, total_size


def check_cluster(market, side):
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=TIME_WINDOW_MINUTES)

    trades = [
        t for t in recent_trades[(market, side)]
        if t["time"] > window_start
    ]

    unique_wallets = set(t["wallet"] for t in trades)

    if len(unique_wallets) >= CLUSTER_THRESHOLD:
        score, total_size = compute_cluster_score(trades)

        confidence = "Weak"
        if score > 70:
            confidence = "Very Strong"
        elif score > 50:
            confidence = "Strong"
        elif score > 30:
            confidence = "Moderate"

        message = f"""
🔥 <b>SMART MONEY CLUSTER</b>

Market: {market}
Direction: {side}
Score: {score}/100
Confidence: {confidence}
Wallets: {len(unique_wallets)}
Total Size: ${int(total_size)}
Time Window: {TIME_WINDOW_MINUTES} min
"""

        send_telegram(message)


def simulate_trade():
    import random

    wallet = random.choice(list(SMART_WALLETS))
    size = random.randint(2000, 10000)
    market = "Example Market"
    side = random.choice(["YES", "NO"])

    trade = {
        "wallet": wallet,
        "size": size,
        "time": datetime.utcnow()
    }

    recent_trades[(market, side)].append(trade)

    check_cluster(market, side)


if __name__ == "__main__":
    send_telegram("🚀 Smart Money Bot Started")

    while True:
        simulate_trade()
        time.sleep(5)
