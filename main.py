from web3 import Web3
import os
import time
import requests
from datetime import datetime, timedelta, timezone

# ==============================
# ENV VARIABLES
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# ==============================
# SETTINGS
# ==============================
CLUSTER_WINDOWS = [5, 30, 60]  # minutes
MIN_WALLETS_FOR_CLUSTER = 3

# ==============================
# WEB3 CONNECTION
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
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message},
            timeout=10
        )
    except:
        pass

# ==============================
# LOAD SMART WALLETS
# ==============================
def load_smart_wallets():
    wallets = set()
    try:
        with open("smart_wallets.txt", "r") as f:
            for line in f:
                wallets.add(line.strip().lower())
    except:
        print("No smart_wallets.txt found.")
    return wallets

smart_wallets = load_smart_wallets()
print(f"Loaded {len(smart_wallets)} smart wallets")

# ==============================
# POLYMARKET API
# ==============================
def get_market_info(token_id_hex):
    try:
        url = f"https://gamma-api.polymarket.com/markets?token_id={token_id_hex}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None

        m = data[0]

        return {
            "question": m.get("question", "Unknown"),
            "outcome": m.get("outcome", "Unknown"),
            "price": float(m.get("price", 0))
        }
    except:
        return None

# ==============================
# STORAGE
# ==============================
trade_history = []
active_clusters = []

# ==============================
# CLUSTER CHECK
# ==============================
def check_clusters():
    now = datetime.now(timezone.utc)

    for window in CLUSTER_WINDOWS:

        cutoff = now - timedelta(minutes=window)

        grouped = {}

        for t in trade_history:
            if t["time"] > cutoff:
                key = (t["question"], t["outcome"])
                grouped.setdefault(key, []).append(t)

        for key, trades in grouped.items():

            if len(trades) >= MIN_WALLETS_FOR_CLUSTER:

                question, outcome = key
                entry_price = trades[-1]["price"]

                send_telegram(
                    f"🚨 CLUSTER DETECTED ({window}m)\n\n"
                    f"Market: {question}\n"
                    f"Side: {outcome}\n"
                    f"Entry Price: {entry_price}\n"
                    f"Wallets: {len(trades)}"
                )

                active_clusters.append({
                    "window": window,
                    "question": question,
                    "outcome": outcome,
                    "entry_price": entry_price,
                    "entry_time": now,
                    "token_id": trades[-1]["token_id"]
                })

# ==============================
# FORWARD RETURN TRACKING
# ==============================
def check_active_clusters():
    now = datetime.now(timezone.utc)

    for cluster in active_clusters[:]:

        minutes_passed = (now - cluster["entry_time"]).total_seconds() / 60

        if minutes_passed >= 5:

            market_info = get_market_info(cluster["token_id"])

            if market_info:
                new_price = market_info["price"]
                entry = cluster["entry_price"]

                if entry > 0:
                    change_pct = ((new_price - entry) / entry) * 100

                    send_telegram(
                        f"📊 RESULT ({cluster['window']}m cluster)\n\n"
                        f"Market: {cluster['question']}\n"
                        f"Return after 5m: {change_pct:.2f}%"
                    )

            active_clusters.remove(cluster)

# ==============================
# MAIN LOOP
# ==============================
if __name__ == "__main__":

    if not w3.is_connected():
        send_telegram("❌ Polygon connection failed")
        exit()

    send_telegram("🚀 Advanced Multi-Window Research Engine Started")

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
                    if len(topics) < 4:
                        continue

                    maker = "0x" + topics[2][-40:]
                    taker = "0x" + topics[3][-40:]

                    if maker.lower() not in smart_wallets and taker.lower() not in smart_wallets:
                        continue

                    data_hex = log["data"].hex()
                    if len(data_hex) < 128:
                        continue

                    token_id = data_hex[64:128]
