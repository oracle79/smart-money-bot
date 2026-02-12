import os
import time
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==============================
# CONFIG
# ==============================

RPC_URL = "https://polygon-mainnet.g.alchemy.com/v2/YOUR_NEW_KEY"

TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

SMART_WALLETS = {
    "0x6d3c5bd13984b2de47c3a88ddc455309aab3d294".lower(),
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf".lower(),
    "0x204f72f35326db932158cba6adff0b9a1da95e14".lower(),
}

# ==============================
# TELEGRAM
# ==============================

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# WEB3 INIT
# ==============================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Fix Polygon POA extraData issue
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("Connected to Polygon")
print("🧠 Smart Wallet Engine Online")
print("Tracking", len(SMART_WALLETS), "wallets")

# ==============================
# MAIN LOOP
# ==============================

last_block = w3.eth.block_number
print("Starting from block:", last_block)

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:

            for block_num in range(last_block + 1, current_block + 1):
                block = w3.eth.get_block(block_num, full_transactions=True)

                for tx in block.transactions:

                    if tx["from"] and tx["from"].lower() in SMART_WALLETS:

                        value_matic = w3.from_wei(tx["value"], "ether")

                        # Only alert if interacting with contract
                        if tx["to"] and tx["value"] == 0:

                            message = f"""
🚨 SMART WALLET CONTRACT INTERACTION

Wallet: {tx['from']}
Block: {block_num}
Tx: https://polygonscan.com/tx/{tx['hash'].hex()}
"""

                            print("Contract interaction detected")
                            send_telegram(message)

            last_block = current_block

        print("Alive | Block", current_block)
        time.sleep(5)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(10)
