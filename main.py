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

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

if __name__ == "__main__":

    if not w3.is_connected():
        send_telegram("❌ Polygon connection failed")
        exit()

    send_telegram("🧪 Debug Mode: Waiting for Fill Event")

    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": POLYMARKET_EXCHANGE,
                    "topics": [FILL_TOPIC]
                })

                for log in logs:

                    tx_hash = log["transactionHash"].hex()
                    topics = [t.hex() for t in log["topics"]]
                    data_hex = log["data"].hex()

                    message = (
                        f"🎯 RAW FILL EVENT\n\n"
                        f"Tx:\n{tx_hash}\n\n"
                        f"Topics:\n{topics}\n\n"
                        f"Data (HEX):\n0x{data_hex}"
                    )

                    send_telegram(message)

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
