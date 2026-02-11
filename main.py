from web3 import Web3
import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload)

if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

    if w3.is_connected():
        send_telegram("✅ Connected to Polygon successfully!")
    else:
        send_telegram("❌ Failed to connect to Polygon.")

    while True:
        time.sleep(60)
