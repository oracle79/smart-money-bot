import os
import time
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from web3 import Web3
from web3.middleware import geth_poa_middleware

# =========================
# ENV VARIABLES (DO NOT CHANGE NAMES)
# =========================
RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =========================
# CONNECT TO POLYGON
# =========================
w3 = Web3(Web3.HTTPProvider(RPC))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon RPC")

# =========================
# SMART WALLETS (YOUR 26)
# =========================
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

# =========================
# TELEGRAM FUNCTION
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# =========================
# CLUSTER MEMORY
# =========================
trade_clusters = defaultdict(list)

# =========================
# FETCH POLYMARKET PRICES
# =========================
def get_market_info(condition_id):
    try:
        r = requests.get(f"https://clob.polymarket.com/markets/{condition_id}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "question": data.get("question", "Unknown"),
                "yes_price": data.get("yesPrice", "N/A"),
                "no_price": data.get("noPrice", "N/A")
            }
    except:
        pass
    return {
        "question": "Unknown",
        "yes_price": "N/A",
        "no_price": "N/A"
    }

# =========================
# STARTUP MESSAGE
# =========================
current_block = w3.eth.block_number

send_telegram(
    f"🧠 Smart Wallet Engine Online\n"
    f"Polygon Block: {current_block}\n"
    f"Monitoring Wallets: {len(SMART_WALLETS)}"
)

print("Monitoring started...")

# =========================
# MAIN LOOP
# =========================
last_block = current_block

while True:
    try:
        latest_block = w3.eth.block_number

        if latest_block > last_block:
            block = w3.eth.get_block(latest_block, full_transactions=True)

            for tx in block.transactions:
                if tx["from"] and tx["from"].lower() in SMART_WALLETS:

                    wallet = tx["from"].lower()
                    value_matic = w3.from_wei(tx["value"], "ether")

                    # Approximate $ value
                    usd_value = float(value_matic) * 0.8  # rough MATIC estimate

                    # LARGE TRADE ALERT
                    if usd_value >= 1000:
                        send_telegram(
                            f"🚨 LARGE TRADE\n\n"
                            f"Wallet: {wallet}\n"
                            f"Est Size: ${int(usd_value)}+\n"
                            f"Block: {latest_block}\n"
                            f"https://polygonscan.com/tx/{tx['hash'].hex()}"
                        )

                    # CLUSTER DETECTION
                    condition_id = tx["to"]
                    direction = "BUY"

                    trade_clusters[(condition_id, direction)].append(
                        (wallet, datetime.utcnow())
                    )

                    # Remove trades older than 1 hour
                    trade_clusters[(condition_id, direction)] = [
                        t for t in trade_clusters[(condition_id, direction)]
                        if t[1] > datetime.utcnow() - timedelta(hours=1)
                    ]

                    wallets_in_cluster = {
                        t[0] for t in trade_clusters[(condition_id, direction)]
                    }

                    if len(wallets_in_cluster) >= 2:
                        market_info = get_market_info(condition_id)

                        send_telegram(
                            f"🔥 CLUSTER ALERT\n\n"
                            f"Contract: {condition_id}\n"
                            f"Event: {market_info['question']}\n"
                            f"Direction: {direction}\n"
                            f"Wallets: {len(wallets_in_cluster)}\n\n"
                            f"YES: {market_info['yes_price']}\n"
                            f"NO: {market_info['no_price']}"
