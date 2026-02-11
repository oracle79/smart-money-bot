from web3 import Web3
import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload)

if __name__ == "__main__":

    if not w3.is_connected():
        send_telegram("❌ Polygon connection failed")
        exit()

    send_telegram("👀 Watching for Polymarket trades...")

    last_block = w3.eth.block_number

    while True:
        current_block = w3.eth.block_number

        if current_block > last_block:
            block = w3.eth.get_block(current_block, full_transactions=True)

            # We will filter transactions here next
            print(f"Scanning block {current_block} with {len(block.transactions)} txs")

            last_block = current_block

        time.sleep(3)
