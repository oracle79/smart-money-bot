from web3 import Web3
import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

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

    send_telegram("🔎 Watching ALL logs from Polymarket contract...")

    last_block = w3.eth.block_number

    while True:
        current_block = w3.eth.block_number

        if current_block > last_block:

            logs = w3.eth.get_logs({
                "fromBlock": last_block + 1,
                "toBlock": current_block,
                "address": POLYMARKET_EXCHANGE
            })

            for for log in logs:
    tx_hash = log["transactionHash"].hex()
    first_topic = log["topics"][0].hex()
    
    send_telegram(
        f"📦 Log Detected\n"
        f"Tx: {tx_hash}\n"
        f"Topic0: {first_topic}"
    )

            last_block = current_block

        time.sleep(3)
