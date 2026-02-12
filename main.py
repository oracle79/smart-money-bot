import os
import time
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# =====================
# ENV
# =====================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if RPC is None:
    raise Exception("RPC missing")

if TELEGRAM_TOKEN is None or TELEGRAM_CHAT_ID is None:
    raise Exception("Telegram missing")

# =====================
# WEB3
# =====================

w3 = Web3(Web3.HTTPProvider(RPC))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Polygon connection failed")

print("Connected to Polygon")
print("Block:", w3.eth.block_number)

# =====================
# SMART WALLETS
# =====================

SMART_WALLETS = set()
SMART_WALLETS.add(w3.to_checksum_address("0x6d3c5bd13984b2de47c3a88ddc455309aab3d294"))
SMART_WALLETS.add(w3.to_checksum_address("0xee613b3fc183ee44f9da9c05f53e2da107e3debf"))
SMART_WALLETS.add(w3.to_checksum_address("0x204f72f35326db932158cba6adff0b9a1da95e14"))

print("Tracking wallets:", len(SMART_WALLETS))

# =====================
# POLYMARKET CONTRACT
# =====================

POLYMARKET_EXCHANGE = w3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

# =====================
# TELEGRAM
# =====================

def send_telegram(msg):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    }
    try:
        requests.post(url, data=data, timeout=10)
    except:
        print("Telegram failed")

send_telegram("Smart Wallet Engine Started")

# =====================
# MAIN LOOP
# =====================

last_block = w3.eth.block_number

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:

            for block_number in range(last_block + 1, current_block + 1):

                block = w3.eth.get_block(block_number, full_transactions=True)

                for tx in block.transactions:

                    if tx["from"] not in SMART_WALLETS:
                        continue

                    if tx["to"] != POLYMARKET_EXCHANGE:
                        continue

                    tx_hash = tx["hash"].hex()

                    message = "Polymarket interaction detected\n"
                    message += "Wallet: " + tx["from"] + "\n"
                    message += "Tx: https://polygonscan.com/tx/" + tx_hash

                    send_telegram(message)

            last_block = current_block

        print("Alive | Block", current_block)
        time.sleep(2)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)
