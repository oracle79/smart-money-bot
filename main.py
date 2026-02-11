from web3 import Web3
import os
import time
import requests
from collections import defaultdict
from datetime import datetime, timedelta
import random

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# ==============================
# CAPITAL & RISK SETTINGS
# ==============================
STARTING_CAPITAL = 1000.0
capital = STARTING_CAPITAL

MAX_RISK_PER_TRADE = 0.02       # 2%
MAX_DAILY_LOSS = 0.05           # 5%
FRACTIONAL_KELLY = 0.25

daily_loss = 0
wins = 0
losses = 0

# ==============================
# SIGNAL SETTINGS
# ==============================
MIN_USDC_SIZE = 100
CLUSTER_WINDOW_SECONDS = 300
MIN_WALLETS_FOR_CLUSTER = 3

# ==============================
# CONNECT WEB3
# ==============================
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"

# ==============================
# TELEGRAM
# ==============================
def send_telegram(message):
    if TELEGRAM_TOKEN is None:
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload)
    except:
        pass

# ==============================
# SMART WALLET FETCH
# ==============================
def fetch_smart_wallets():
    try:
        response = requests.get(
            "https://data-api.polymarket.com/v1/leaderboard",
            params={"timePeriod": "WEEK", "orderBy": "PNL", "limit": 500},
            timeout=10
        )
        data = response.json()
    except:
        return set()

    wallets = set()
    for trader in data:
        wallet = trader.get("proxyWallet")
        if wallet:
            wallets.add(wallet.lower())

    return wallets

SMART_WALLETS = fetch_smart_wallets()

# ==============================
# CLUSTER ENGINE
# ==============================
recent_trades = []

def clean_old_trades():
    cutoff = datetime.utcnow() - timedelta(seconds=CLUSTER_WINDOW_SECONDS)
    return [t for t in recent_trades if t["time"] > cutoff]

def calculate_position_size(edge_estimate=0.05):
    global capital

    if wins + losses < 10:
        kelly_fraction = MAX_RISK_PER_TRADE
    else:
        win_rate = wins / (wins + losses)
        b = 1  # assume 1:1 payoff
        kelly = (win_rate * (b + 1) - 1) / b
        kelly_fraction = max(0, kelly * FRACTIONAL_KELLY)

    kelly_fraction = min(kelly_fraction, MAX_RISK_PER_TRADE)
    return capital * kelly_fraction

# ==============================
# PAPER TRADING ENGINE
# ==============================
open_positions = []

def simulate_trade(signal_score):
    global capital, wins, losses, daily_loss

    if daily_loss >= STARTING_CAPITAL * MAX_DAILY_LOSS:
        print("Daily loss limit hit. No trading.")
        return

    position_size = calculate_position_size()

    if position_size <= 0:
        return

    # Placeholder simulated outcome
    win_probability = min(0.5 + signal_score / 200, 0.75)

    if random.random() < win_probability:
        profit = position_size
        capital += profit
        wins += 1
        send_telegram(f"📈 PAPER WIN +${profit:.2f} | Capital: ${capital:.2f}")
    else:
        loss = position_size
        capital -= loss
        daily_loss += loss
        losses += 1
        send_telegram(f"📉 PAPER LOSS -${loss:.2f} | Capital: ${capital:.2f}")

# ==============================
# MAIN LOOP
# ==============================
if __name__ == "__main__":

    if not w3.is_connected():
        print("Polygon connection failed")
        exit()

    send_telegram("🚀 Paper Trading Engine Started")

    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": POLYMARKET_EXCHANGE,
                    "topics": [FILL_TOPIC]
                })

                for log in logs:
                    topics = [t.hex() for t in log["topics"]]
                    taker = "0x" + topics[3][-40:]

                    if taker.lower() not in SMART_WALLETS:
                        continue

                    data_hex = log["data"].hex()
                    chunks = [data_hex[i:i+64] for i in range(0, len(data_hex), 64)]

                    if len(chunks) < 4:
                        continue

                    raw_amount = int(chunks[3], 16)
                    usdc_amount = raw_amount / 1_000_000

                    if usdc_amount < MIN_USDC_SIZE:
                        continue

                    recent_trades.append({
                        "wallet": taker,
                        "market": topics[1],
                        "time": datetime.utcnow()
                    })

                    recent_trades[:] = clean_old_trades()

                    grouped = defaultdict(list)
                    for trade in recent_trades:
                        grouped[trade["market"]].append(trade)

                    for market, trades in grouped.items():
                        unique_wallets = set(t["wallet"] for t in trades)

                        if
