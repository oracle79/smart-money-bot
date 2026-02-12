import os
import time
import requests
from web3 import Web3

# ===============================
# ENV VARIABLES
# ===============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# ===============================
# CONNECT TO POLYGON
# ===============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Web3 failed to connect")

block = w3.eth.block_number
print(f"🚀 Quant Engine Online | Polygon Block: {block}")

# ===============================
# TELEGRAM FUNCTION
# ===============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

send_telegram(f"🚀 Quant Engine Connected\nBlock: {block}")

# ===============================
# BLOCK MONITOR LOOP
# ===============================

last_block = block

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:
            print(f"New Block: {current_block}")
            last_block = current_block

        time.sleep(5)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
