import os
import time
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from web3 import Web3
from web3.middleware.geth_poa import geth_poa_middleware

# ==============================
# ENV VARIABLES
# ==============================
RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# ==============================
# CONNECT TO POLYGON
# ==============================
w3 = Web3(Web3.HTTPProvider(RPC))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

# ==============================
# SMART WALLETS (26)
# ==============================
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

# ==============================
# TELEGRAM FUNCTION
# ==============================
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

# ==============================
# CLUSTER STORAGE
# ==============================
trade_clusters = defaultdict(list)

# ==============================
# FETCH POLYMARKET MARKET INFO
# ==============================
def get_market_info(contract_address):
    try:
        r = requests.get(
            f"https://clob.polymarket.com/markets/{contract_address}",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return (
                data.get("question", "Unknown"),
                data.get("yesPrice", "N/A"),
                data.get("noPrice", "N/A")
            )
    except Exception:
        pass
    return ("Unknown", "N/A", "N/A")

# ==============================
# STARTUP MESSAGE
# ==============================
current_block = w3.eth.block_number

send_telegram(
    f"🧠 Smart Wallet Engine Online\n"
    f"Polygon Block: {current_block}\n"
    f"Monitoring Wallets: {len(SMART_WALLETS)}"
)

print("Engine running...")

# ==============================
# MAIN LOOP
# ==============================
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
                    usd_estimate = float(value_matic) * 0.8

                    # -----------------
                    # LARGE TRADE ALERT
                    # -----------------
                    if usd_estimate >= 1000:
                        send_telegram(
                            f"🚨 LARGE TRADE\n\n"
                            f"Wallet: {wallet}\n"
                            f"Est Size: ${int(usd_estimate)}+\n"
                            f"Block: {latest_block}\n"
                            f"https://polygonscan.com/tx/{tx['hash'].hex()}"
                        )

                    # -----------------
                    # CLUSTER DETECTION
                    # -----------------
                    contract = tx["to"]
                    direction = "BUY"

                    trade_clusters[(contract, direction)].append(
                        (wallet, datetime.utcnow())
                    )

                    # Remove >1h old
                    trade_clusters[(contract, direction)] = [
                        t for t in trade_clusters[(contract, direction)]
                        if t[1] > datetime.utcnow() - timedelta(hours=1)
                    ]

                    wallets = {
                        t[0] for t in trade_clusters[(contract, direction)]
                    }

                    if len(wallets) >= 2:
                        question, yes_price, no_price = get_market_info(contract)

                        send_telegram(
                            f"🔥 CLUSTER ALERT\n\n"
                            f"Contract: {contract}\n"
                            f"Event: {question}\n"
                            f"Wallets: {len(wallets)}\n\n"
                            f"YES: {yes_price}\n"
                            f"NO: {no_price}"
                        )

            last_block = latest_block

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
