import os
import time
import requests
from datetime import datetime, timedelta
from web3 import Web3

# ================================
# ENV VARIABLES
# ================================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram variables not set")

# ================================
# CONNECT TO POLYGON
# ================================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("🧠 Internal Smart Wallet Leaderboard Engine Online")
print("Polygon Block:", w3.eth.block_number)

# ================================
# CONFIG
# ================================

USDC_CONTRACT = Web3.to_checksum_address(
    "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
)

MIN_TRADE_SIZE = 1000  # $1000 filter
TOP_WALLET_LIMIT = 500
CLUSTER_THRESHOLD = 3
CLUSTER_WINDOW_MINUTES = 60

# ================================
# DATA STORAGE
# ================================

wallet_stats = {}
cluster_memory = []

last_dashboard = time.time()

# ================================
# TELEGRAM
# ================================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# ================================
# UPDATE WALLET STATS
# ================================

def update_wallet(wallet, amount):
    if wallet not in wallet_stats:
        wallet_stats[wallet] = {
            "total_volume": 0,
            "total_trades": 0,
            "avg_trade_size": 0,
            "last_active": datetime.utcnow()
        }

    stats = wallet_stats[wallet]

    stats["total_volume"] += amount
    stats["total_trades"] += 1
    stats["avg_trade_size"] = stats["total_volume"] / stats["total_trades"]
    stats["last_active"] = datetime.utcnow()

# ================================
# CALCULATE WALLET SCORE
# ================================

def calculate_score(stats):
    volume_weight = 0.5
    trade_weight = 0.3
    conviction_weight = 0.2

    return (
        volume_weight * stats["total_volume"]
        + trade_weight * stats["total_trades"] * 100
        + conviction_weight * stats["avg_trade_size"]
    )

# ================================
# GET TOP 500
# ================================

def get_top_wallets():
    scored = []

    for wallet, stats in wallet_stats.items():
        score = calculate_score(stats)
        scored.append((wallet, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [w[0] for w in scored[:TOP_WALLET_LIMIT]]

# ================================
# CLUSTER DETECTION
# ================================

def check_cluster(wallet, amount):
    now = datetime.utcnow()
    cluster_memory.append((wallet, now))

    # remove old entries
    cluster_memory[:] = [
        entry for entry in cluster_memory
        if now - entry[1] < timedelta(minutes=CLUSTER_WINDOW_MINUTES)
    ]

    unique_wallets = set([entry[0] for entry in cluster_memory])

    if len(unique_wallets) >= CLUSTER_THRESHOLD:
        send_telegram(
            f"🔥 CLUSTER ALERT\n\n"
            f"{len(unique_wallets)} Top Wallets Active\n"
            f"Window: {CLUSTER_WINDOW_MINUTES} min\n"
            f"Potential coordinated move detected"
        )
        cluster_memory.clear()

# ================================
# MAIN LOOP
# ================================

def main_loop():
    global last_dashboard

    latest_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > latest_block:
                for block_number in range(latest_block + 1, current_block + 1):
                    block = w3.eth.get_block(block_number, full_transactions=True)

                    for tx in block.transactions:
                        if tx.to and tx.to.lower() == USDC_CONTRACT.lower():
                            value = tx.value / 1e6

                            if value >= MIN_TRADE_SIZE:
                                wallet = tx["from"]

                                update_wallet(wallet, value)

                                top_wallets = get_top_wallets()

                                if wallet in top_wallets:
                                    send_telegram(
                                        f"🚨 LARGE TRADE\n\n"
                                        f"Wallet: {wallet}\n"
                                        f"Size: ${int(value)}\n"
                                        f"Block: {block_number}\n"
                                        f"https://polygonscan.com/tx/{tx.hash.hex()}"
                                    )

                                    check_cluster(wallet, value)

                latest_block = current_block

            # Dashboard every 10 min
            if time.time() - last_dashboard > 600:
                top_wallets = get_top_wallets()

                send_telegram(
                    f"📊 INTERNAL LEADERBOARD UPDATE\n\n"
                    f"Tracked Wallets: {len(wallet_stats)}\n"
                    f"Top Wallets: {len(top_wallets)}\n"
                    f"Min Trade Size: ${MIN_TRADE_SIZE}"
                )

                last_dashboard = time.time()

            time.sleep(5)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# ================================
# START ENGINE
# ================================

send_telegram("🧠 Internal Smart Wallet Leaderboard Engine Started")

main_loop()
