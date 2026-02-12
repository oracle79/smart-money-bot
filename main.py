import os
import time
import requests
from web3 import Web3
from datetime import datetime
from collections import defaultdict

# =====================================
# ENV VARIABLES (DO NOT CHANGE NAMES)
# =====================================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =====================================
# CONNECT TO POLYGON
# =====================================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon RPC")

print("✅ Connected to Polygon")

# =====================================
# TELEGRAM FUNCTION
# =====================================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# =====================================
# SMART WALLET LIST
# PASTE TOP 100 WEEKLY WINNERS BELOW
# =====================================

SMART_WALLETS = set([
    # Example format:
    # "0xabc123...",
    # "0xdef456...",
])

# Normalize to lowercase
SMART_WALLETS = set([w.lower() for w in SMART_WALLETS])

# =====================================
# CLUSTER MEMORY
# =====================================

cluster_memory = defaultdict(lambda: {"YES": set(), "NO": set()})

# =====================================
# SIMPLE DIRECTION DETECTOR (TEMP)
# =====================================

def detect_direction(tx):
    if int(tx["value"]) > 0:
        return "YES"
    return "NO"

# =====================================
# BOOT MESSAGE
# =====================================

current_block = w3.eth.block_number

send_telegram(
    f"🧠 Smart Wallet Quant Engine v1 Online\n"
    f"Polygon Block: {current_block}\n"
    f"Tracking Wallets: {len(SMART_WALLETS)}"
)

print("🚀 Engine Running")
print("Tracking wallets:", len(SMART_WALLETS))

# =====================================
# MAIN LOOP
# =====================================

last_checked_block = current_block

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_checked_block:
            for block_number in range(last_checked_block + 1, current_block + 1):
                block = w3.eth.get_block(block_number, full_transactions=True)

                for tx in block.transactions:
                    sender = tx["from"].lower()

                    if sender in SMART_WALLETS:

                        direction = detect_direction(tx)
                        contract = tx["to"]

                        # Single wallet alert
                        send_telegram(
                            f"🧠 Smart Wallet Trade\n"
                            f"Wallet: {sender}\n"
                            f"Contract: {contract}\n"
                            f"Direction: {direction}\n"
                            f"Block: {block_number}"
                        )

                        # Cluster tracking
                        cluster_memory[contract][direction].add(sender)

                        if len(cluster_memory[contract][direction]) >= 3:
                            send_telegram(
                                f"🚨 CLUSTER ALERT\n"
                                f"Contract: {contract}\n"
                                f"Direction: {direction}\n"
                                f"Wallets: {len(cluster_memory[contract][direction])}"
                            )

            last_checked_block = current_block

        time.sleep(5)

    except Exception as e:
        print("Engine error:", e)
        time.sleep(5)
