import os
import time
import requests
from web3 import Web3
from datetime import datetime, timezone

# =============================
# ENV VARIABLES
# =============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set in Railway variables")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =============================
# CONNECT WEB3
# =============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon RPC")

print("✅ Connected to Polygon")

current_block = w3.eth.block_number
print(f"📦 Current Block: {current_block}")

# =============================
# TELEGRAM
# =============================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

send_telegram("🧠 Smart Cluster Quant Engine v3 Online")

# =============================
# SAFE BLOCK POLLER
# =============================

def get_block_safe(block_number):
    try:
        return w3.eth.get_block(block_number, full_transactions=True)
    except Exception as e:
        print("Block fetch error:", e)
        return None

# =============================
# MAIN LOOP
# =============================

last_checked_block = current_block

print("🚀 Monitoring new blocks...")

while True:
    try:
        latest_block = w3.eth.block_number

        if latest_block > last_checked_block:
            for block_num in range(last_checked_block + 1, latest_block + 1):

                print(f"🔎 Scanning block {block_num}")

                block = get_block_safe(block_num)
                if block is None:
                    continue

                for tx in block.transactions:
                    # Simple logging for now
                    print("TX:", tx.hash.hex())

            last_checked_block = latest_block

        time.sleep(3)

    except Exception as e:
        print("Main loop error:", e)
        time.sleep(5)
