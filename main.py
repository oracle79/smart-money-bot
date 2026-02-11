from web3 import Web3
import os
import time
import requests

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# Connect to Polygon
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

# Polymarket Exchange Contract (Polygon Mainnet)
POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

if __name__ == "__main__":

    if not w3.is_connected():
        print("❌ Polygon connection failed")
        send_telegram("❌ Polygon connection failed")
        exit()

    print("✅ Connected to Polygon")
    send_telegram("🔎 Inspecting Polymarket log Topic0 values...")

    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:

                print(f"Scanning block {current_block}")

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": POLYMARKET_EXCHANGE
                })

                for log in logs:
                    tx_hash = log["transactionHash"].hex()
                    topic0 = "0x" + log["topics"][0].hex()

                    message = (
                        f"📦 Polymarket Log Detected\n"
                        f"Tx: {tx_hash}\n"
                        f"Topic0: {topic0}"
                    )

                    print(message)
                    send_telegram(message)

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
