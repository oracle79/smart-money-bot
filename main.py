import time
import threading
import requests
from flask import Flask
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==========================================
# CONFIG (HARDCODED FOR SIMPLICITY)
# ==========================================

ALCHEMY_URL = "https://polygon-mainnet.g.alchemy.com/v2/5C0VcEocSzKMERi35xguh"
TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
CHAT_ID = "7154046718"

SMART_WALLETS = {
    "0x6d3c5bd13984b2de47c3a88ddc455309aab3d294".lower(),
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf".lower(),
    "0x204f72f35326db932158cba6adff0b9a1da95e14".lower()
}

POLL_DELAY = 8  # seconds between checks

# ==========================================
# CONNECT TO POLYGON
# ==========================================

w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("Connected to Polygon")

# ==========================================
# TELEGRAM FUNCTION
# ==========================================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

# ==========================================
# MONITOR ENGINE
# ==========================================

def monitor():
    print("🧠 Smart Wallet Engine Online")
    print(f"Tracking {len(SMART_WALLETS)} wallets")

    # SEND STARTUP MESSAGE (CONFIRMS TELEGRAM WORKS)
    send_telegram("✅ Smart Wallet Engine Started and Monitoring")

    last_block = w3.eth.block_number
    print(f"Starting from block: {last_block}")

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                block = w3.eth.get_block(current_block, full_transactions=True)

                for tx in block.transactions:
                    sender = tx.get("from")

                    if sender and sender.lower() in SMART_WALLETS:
                        value_matic = w3.from_wei(tx["value"], "ether")

                        message = (
                            "🔥 Smart Wallet Transaction Detected\n\n"
                            f"Wallet: {sender}\n"
                            f"Block: {current_block}\n"
                            f"Value: {value_matic} MATIC\n"
                            f"https://polygonscan.com/tx/{tx['hash'].hex()}"
                        )

                        print(message)
                        send_telegram(message)

                last_block = current_block

            print(f"Alive | Block {current_block}")
            time.sleep(POLL_DELAY)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(15)

# ==========================================
# FLASK SERVER (KEEPS RAILWAY ALIVE)
# ==========================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Smart Wallet Engine Running"

# START MONITOR IN BACKGROUND
threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
