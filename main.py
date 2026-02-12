import time
import threading
import requests
from flask import Flask
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==========================================
# CONFIG
# ==========================================

ALCHEMY_URL = "https://polygon-mainnet.g.alchemy.com/v2/5C0VcEocSzKMERi35xguh"
TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
CHAT_ID = "7154046718"

POLYMARKET_EXCHANGE = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045".lower()

SMART_WALLETS = {
    "0x6d3c5bd13984b2de47c3a88ddc455309aab3d294".lower(),
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf".lower(),
    "0x204f72f35326db932158cba6adff0b9a1da95e14".lower()
}

POLL_DELAY = 8

# ==========================================
# CONNECT
# ==========================================

w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("Connected to Polygon")

# ==========================================
# TELEGRAM
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
# HELPER: Decode YES / NO
# ==========================================

def decode_yes_no(input_data):
    # Very simplified logic:
    # YES token usually ends in 01
    # NO token usually ends in 00
    # This is heuristic but works for binary ERC1155 ids

    if input_data.endswith("01"):
        return "YES"
    elif input_data.endswith("00"):
        return "NO"
    else:
        return "UNKNOWN"

# ==========================================
# MONITOR
# ==========================================

def monitor():
    print("🧠 Smart Wallet Engine Online")
    print(f"Tracking {len(SMART_WALLETS)} wallets")

    send_telegram("✅ Smart Wallet Engine Monitoring Polymarket Trades")

    last_block = w3.eth.block_number
    print(f"Starting from block: {last_block}")

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                block = w3.eth.get_block(current_block, full_transactions=True)

                for tx in block.transactions:
                    sender = tx.get("from")
                    receiver = tx.get("to")

                    if not sender or not receiver:
                        continue

                    sender = sender.lower()
                    receiver = receiver.lower()

                    # Filter smart wallets
                    if sender in SMART_WALLETS:

                        # Filter Polymarket contract only
                        if receiver == POLYMARKET_EXCHANGE:

                            tx_hash = tx["hash"].hex()
                            input_data = tx["input"]

                            direction = decode_yes_no(input_data)

                            message = (
                                "🎯 POLYMARKET TRADE DETECTED\n\n"
                                f"Wallet: {sender}\n"
                                f"Direction: {direction}\n"
                                f"Block: {current_block}\n"
                                f"https://polygonscan.com/tx/{tx_hash}"
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
# FLASK SERVER
# ==========================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Smart Wallet Polymarket Engine Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
