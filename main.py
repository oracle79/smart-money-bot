import os
import time
import threading
from flask import Flask
from web3 import Web3

# ===============================
# ENV VARIABLES
# ===============================
RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

# ===============================
# WEB SERVER (Keeps Railway Alive)
# ===============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Smart Wallet Engine Running"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# ===============================
# WEB3 SETUP
# ===============================
w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("Connected to Polygon")
print("🧠 Smart Wallet Engine Online")

# ===============================
# TRACKED WALLETS
# ===============================
SMART_WALLETS = [
    "0x6d3c5bd13984b2de47c3a88ddc455309aab3d294",
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf",
    "0x204f72f35326db932158cba6adff0b9a1da95e14",
]

print(f"Tracking {len(SMART_WALLETS)} wallets")

# ===============================
# MAIN LOOP
# ===============================
def run_engine():
    last_block = w3.eth.block_number
    print(f"Starting from block: {last_block}")

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                print(f"Alive | Block {current_block}")
                last_block = current_block

            time.sleep(5)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(10)

# ===============================
# START EVERYTHING
# ===============================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_engine()
