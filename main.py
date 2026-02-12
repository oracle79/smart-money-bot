import os
import time
import requests
from web3 import Web3
from collections import defaultdict
from datetime import datetime, timezone

# =============================
# ENV
# =============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =============================
# WEB3
# =============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Web3 failed to connect")

print("🧠 Smart Wallet Quant Engine v2 Online")
print("Polygon Block:", w3.eth.block_number)

EXCHANGE_ADDRESS = Web3.to_checksum_address(
    "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
)

# =============================
# TELEGRAM
# =============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# =============================
# BUILD WEEKLY TOP WALLET LIST
# =============================

def build_top_wallets():

    print("🔍 Building weekly leaderboard from chain...")

    current_block = w3.eth.block_number
    blocks_per_day = 43000  # approx Polygon
    seven_days_blocks = blocks_per_day * 7

    start_block = current_block - seven_days_blocks

    wallet_volume = defaultdict(int)

    try:
        logs = w3.eth.get_logs({
            "fromBlock": start_block,
            "toBlock": current_block,
            "address": EXCHANGE_ADDRESS
        })

        print(f"Logs fetched: {len(logs)}")

        for log in logs:
            tx = w3.eth.get_transaction(log["transactionHash"])
            wallet = tx["from"]

            # simple proxy metric: count trades
            wallet_volume[wallet] += 1

    except Exception as e:
        print("Leaderboard build failed:", e)
        return set()

    # sort wallets by trade count
    sorted_wallets = sorted(
        wallet_volume.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top_wallets = [w for w, v in sorted_wallets[:400]]

    print(f"Top wallets selected: {len(top_wallets)}")

    return set(top_wallets)

# =============================
# BUILD INITIAL LIST
# =============================

TRACKED_WALLETS = build_top_wallets()

print("Tracking Wallets:", len(TRACKED_WALLETS))

send_telegram(f"✅ Wallet monitoring started\nTracked wallets: {len(TRACKED_WALLETS)}")

# =============================
# CLUSTER ENGINE
# =============================

CLUSTER_WINDOW_SECONDS = 600
CLUSTER_THRESHOLD = 5

cluster_tracker = defaultdict(list)

def clean_old():
    now = time.time()
    for key in list(cluster_tracker.keys()):
        cluster_tracker[key] = [
            t for t in cluster_tracker[key]
            if now - t < CLUSTER_WINDOW_SECONDS
        ]
        if not cluster_tracker[key]:
            del cluster_tracker[key]

# =============================
# LIVE MONITOR
# =============================

last_block = w3.eth.block_number

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:

            logs = w3.eth.get_logs({
                "fromBlock": last_block + 1,
                "toBlock": current_block,
                "address": EXCHANGE_ADDRESS
            })

            for log in logs:

                tx = w3.eth.get_transaction(log["transactionHash"])
                wallet = tx["from"]

                if wallet not in TRACKED_WALLETS:
                    continue

                market_id = log["address"]
                key = (market_id, "FLOW")

                cluster_tracker[key].append(time.time())
                clean_old()

                if len(cluster_tracker[key]) >= CLUSTER_THRESHOLD:

                    message = (
                        "🚨 CLUSTER ALERT\n\n"
                        f"Market: {market_id}\n"
                        f"Wallet Count: {len(cluster_tracker[key])}\n"
                        f"Window: {CLUSTER_WINDOW_SECONDS//60}m\n"
                        f"Block: {current_block}"
                    )

                    send_telegram(message)
                    cluster_tracker[key] = []

            last_block = current_block

        time.sleep(3)

    except Exception as e:
        print("Live loop error:", e)
        time.sleep(5)
