from web3 import Web3
import os
import time
import requests
from collections import defaultdict
from datetime import datetime, timedelta

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# ==============================
# CONFIG
# ==============================
LEADERBOARD_API = "https://data-api.polymarket.com/v1/leaderboard"
TIME_PERIOD = "WEEK"
LIMIT = 500

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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# LOAD SMART WALLETS
# ==============================

def fetch_smart_wallets():
    params = {
        "timePeriod": TIME_PERIOD,
        "orderBy": "PNL",
        "limit": LIMIT
    }

    try:
        response = requests.get(LEADERBOARD_API, params=params, timeout=10)
        data = response.json()
    except Exception as e:
        print("Leaderboard fetch error:", e)
        return set()

    wallets = set()
    for trader in data:
        wallet = trader.get("proxyWallet")
        if wallet:
            wallets.add(wallet.lower())

    print(f"Loaded {len(wallets)} smart wallets")
    return wallets

# ==============================
# CLUSTER ENGINE
# ==============================

recent_trades = []

def clean_old_trades():
    global recent_trades
    cutoff = datetime.utcnow() - timedelta(seconds=CLUSTER_WINDOW_SECONDS)
    recent_trades = [t for t in recent_trades if t["time"] > cutoff]

def check_clusters():
    market_groups = defaultdict(list)

    for trade in recent_trades:
        key = (trade["market"], trade["direction"])
        market_groups[key].append(trade)

    for key, trades in market_groups.items():
        unique_wallets = set(t["wallet"] for t in trades)

        if len(unique_wallets) >= MIN_WALLETS_FOR_CLUSTER:
            total_size = sum(t["size"] for t in trades)

            cluster_score = len(unique_wallets) * 10 + total_size * 0.01

            message = (
                f"🚨 CLUSTER DETECTED\n\n"
                f"Market: {key[0]}\n"
                f"Direction: {key[1]}\n"
                f"Wallets: {len(unique_wallets)}\n"
                f"Total Size: ${total_size:,.2f}\n"
                f"Cluster Score: {cluster_score:.2f}"
            )

            send_telegram(message)

            # Clear trades to avoid duplicate alerts
            recent_trades.clear()
            break

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    if not w3.is_connected():
        print("Polygon connection failed")
        exit()

    send_telegram("🚀 Professional Cluster Engine Started")

    SMART_WALLETS = fetch_smart_wallets()

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
                    tx_hash = log["transactionHash"].hex()

                    maker = "0x" + topics[2][-40:]
                    taker = "0x" + topics[3][-40:]

                    data_hex = log["data"].hex()
                    chunks = [data_hex[i:i+64] for i in range(0, len(data_hex), 64)]

                    if len(chunks) < 4:
                        continue

                    raw_amount = int(chunks[3], 16)
                    usdc_amount = raw_amount / 1_000_000

                    if usdc_amount < MIN_USDC_SIZE:
                        continue

                    if taker.lower() not in SMART_WALLETS:
                        continue

                    market_id = topics[1]
                    direction = "UNKNOWN"

                    trade_data = {
                        "wallet": taker.lower(),
                        "market": market_id,
                        "direction": direction,
                        "size": usdc_amount,
                        "time": datetime.utcnow()
                    }

                    recent_trades.append(trade_data)

                    clean_old_trades()
                    check_clusters()

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
