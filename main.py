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
CLUSTER_WINDOW_SECONDS = 300
MIN_WALLETS_FOR_CLUSTER = 3
MIN_TRADE_SIZE = 100

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

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=10)
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
# POLYMARKET API LOOKUP
# ==============================
def get_market_info(token_id_hex):
    try:
        url = f"https://gamma-api.polymarket.com/markets?token_id={token_id_hex}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        if not data:
            return None

        market = data[0]

        return {
            "question": market.get("question", "Unknown"),
            "outcome": market.get("outcome", "Unknown"),
            "price": float(market.get("price", 0))
        }

    except:
        return None

# ==============================
# CLUSTER STORAGE
# ==============================
recent_trades = []
active_clusters = []

# ==============================
# CHECK CLUSTER
# ==============================
def check_cluster():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=CLUSTER_WINDOW_SECONDS)

    valid = [t for t in recent_trades if t["time"] > cutoff]

    if len(valid) >= MIN_WALLETS_FOR_CLUSTER:
        cluster = valid[-1]

        send_telegram(
            f"🚨 CLUSTER DETECTED\n\n"
            f"Market: {cluster['question']}\n"
            f"Side: {cluster['outcome']}\n"
            f"Entry Price: {cluster['price']}\n"
            f"Wallets: {len(valid)}"
        )

        active_clusters.append({
            "question": cluster["question"],
            "outcome": cluster["outcome"],
            "entry_price": cluster["price"],
            "entry_time": now,
            "token_id": cluster["token_id"]
        })

# ==============================
# TRACK FORWARD RETURNS
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

                change_pct = ((new_price - entry) / entry) * 100

                send_telegram(
                    f"📊 CLUSTER RESULT (5m)\n\n"
                    f"Market: {cluster['question']}\n"
                    f"Side: {cluster['outcome']}\n"
                    f"Return: {change_pct:.2f}%"
                )

            active_clusters.remove(cluster)

# ==============================
# MAIN LOOP
# ==============================
if __name__ == "__main__":

    if not w3.is_connected():
        send_telegram("❌ Polygon connection failed")
        exit()

    send_telegram("🚀 Alpha Measurement Engine Started")

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

                    # Split 32-byte chunks
                    token_id = data_hex[64:128]

                    market_info = get_market_info(token_id)

                    if not market_info:
                        continue

                    price = market_info["price"]

                    if price <= 0:
                        continue

                    recent_trades.append({
                        "time": datetime.now(timezone.utc),
                        "question": market_info["question"],
                        "outcome": market_info["outcome"],
                        "price": price,
                        "token_id": token_id
                    })

                    check_cluster()

                last_block = current_block

            check_active_clusters()

            time.sleep(5)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
