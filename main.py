import os
import time
import requests
from collections import defaultdict
from web3 import Web3

# =============================
# ENV VARIABLES
# =============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =============================
# WEB3 SETUP
# =============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Web3 failed to connect")

print("🧠 Smart Wallet Cluster Engine Online")
print("Polygon Block:", w3.eth.block_number)

# =============================
# SMART WALLETS
# =============================

SMART_WALLETS = {
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e",
    "0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee",
    "0x14964aefa2cd7caff7878b3820a690a03c5aa429",
    "0x1d8a377c5020f612ce63a0a151970df64baae842",
    "0x876426b52898c295848f56760dd24b55eda2604a",
    "0xd6a3f0ec6c4a8ad680d580610c82ca57ff139489",
    "0x6211f97a76ed5c4b1d658f637041ac5f293db89e",
    "0x003932bc605249fbfeb9ea6c3e15ec6e868a6beb",
    "0x04a39d068f4301195c25dcb4c1fe5a4f08a65213",
    "0xccb290b1c145d1c95695d3756346bba9f1398586",
    "0x99bd18bf3b49a82cbd5749eafb3bfb117406238e",
    "0xa8e089ade142c95538e06196e09c85681112ad50",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea",
    "0x5da48936d61eb18d66ca5fdd32ba2d2ba19be203",
    "0x7e6fda10646a4343358c84004859adfea1c0c022",
    "0x72b40c0012682ef52228ad53ef955f9e4f177d67",
    "0x37e4728b3c4607fb2b3b205386bb1d1fb1a8c991",
    "0x93abbc022ce98d6f45d4444b594791cc4b7a9723",
    "0x63ce342161250d705dc0b16df89036c8e5f9ba9a",
    "0x6e82b93eb57b01a63027bd0c6d2f3f04934a752c",
    "0x0b9cae2b0dfe7a71c413e0604eaac1c352f87e44",
    "0x4cbfc0c337dde457f7963b62fb57678ca1286cf0",
    "0x19f19dd8ee1f7e5f6ec666987e2963a65971a9c6",
    "0x96489abcb9f583d6835c8ef95ffc923d05a86825",
    "0x3b5c629f114098b0dee345fb78b7a3a013c7126e",
    "0x1057e7d3ddafc60a4aeb10a2bc5b543792449ea5"
}

print("Tracking Wallets:", len(SMART_WALLETS))

# =============================
# TELEGRAM
# =============================

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

# =============================
# POLYMARKET API HELPERS
# =============================

def fetch_market_info(contract):
    try:
        url = f"https://gamma-api.polymarket.com/markets?clobTokenIds={contract}"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        if not data:
            return None

        market = data[0]

        return {
            "event": market.get("eventSlug", "Unknown Event"),
            "question": market.get("question", "Unknown Market"),
            "yes_price": market.get("outcomes", [{}])[0].get("price", "N/A"),
            "no_price": market.get("outcomes", [{}])[-1].get("price", "N/A"),
        }

    except:
        return None

# =============================
# SETTINGS
# =============================

CLUSTER_WINDOW = 3600
CLUSTER_THRESHOLD = 2
LARGE_TRADE_THRESHOLD = 1000

trade_clusters = defaultdict(list)
last_block = w3.eth.block_number

send_telegram(f"🚀 Monitoring Started\nWallets: {len(SMART_WALLETS)}")

# =============================
# MAIN LOOP
# =============================

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:
            for block_num in range(last_block + 1, current_block + 1):
                block = w3.eth.get_block(block_num, full_transactions=True)

                for tx in block.transactions:
                    from_addr = tx["from"].lower()

                    if from_addr in SMART_WALLETS:

                        contract = tx["to"]
                        direction = "YES"

                        key = (contract, direction)
                        trade_clusters[key].append((from_addr, time.time()))

                        trade_clusters[key] = [
                            (w, t)
                            for w, t in trade_clusters[key]
                            if time.time() - t <= CLUSTER_WINDOW
                        ]

                        unique_wallets = set(w for w, _ in trade_clusters[key])

                        if len(unique_wallets) >= CLUSTER_THRESHOLD:

                            market_info = fetch_market_info(contract)

                            if market_info:
                                send_telegram(
                                    f"🔥 CLUSTER ALERT\n\n"
                                    f"Event: {market_info['event']}\n"
                                    f"Market: {market_info['question']}\n"
                                    f"Direction: {direction}\n"
                                    f"YES Price: {market_info['yes_price']}\n"
                                    f"NO Price: {market_info['no_price']}\n"
                                    f"Wallets: {len(unique_wallets)}\n"
                                    f"Contract: {contract}"
                                )
                            else:
                                send_telegram(
                                    f"🔥 CLUSTER ALERT\n"
                                    f"Contract: {contract}\n"
                                    f"Wallets: {len(unique_wallets)}"
                                )

            last_block = current_block

        time.sleep(3)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
