import os
import time
import requests
from web3 import Web3
from datetime import datetime

# ==============================
# ENV VARIABLES
# ==============================

RPC_URL = os.getenv("RPC_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC_URL:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# ==============================
# WEB3 CONNECTION
# ==============================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("✅ Connected to Polygon")
print("🧠 Smart Cluster Quant Engine v4 Online")

POLYMARKET_CONTRACT = Web3.to_checksum_address(
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
)

# ==============================
# TELEGRAM FUNCTION
# ==============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# BASIC TRADE DETECTOR
# ==============================

last_block = w3.eth.block_number
print(f"📦 Starting from block {last_block}")

def process_block(block_number):
    block = w3.eth.get_block(block_number, full_transactions=True)

    for tx in block.transactions:
        if tx.to and tx.to.lower() == POLYMARKET_CONTRACT.lower():

            wallet = tx["from"]
            value = w3.from_wei(tx["value"], "ether")

            message = (
                f"📊 Polymarket Contract Activity\n"
                f"Block: {block_number}\n"
                f"Wallet: {wallet}\n"
                f"Value: {value} MATIC\n"
                f"Tx: {tx.hash.hex()}\n"
                f"Time: {datetime.utcnow()}"
            )

            print("🔥 Polymarket Tx Detected")
            print(message)

            send_telegram(message)

# ==============================
# MAIN LOOP
# ==============================

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:
            for b in range(last_block + 1, current_block + 1):
                process_block(b)
            last_block = current_block

        time.sleep(2)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
