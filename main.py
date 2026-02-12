import time
import threading
import requests
from flask import Flask
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# =========================
# CONFIG
# =========================

ALCHEMY_URL = "https://polygon-mainnet.g.alchemy.com/v2/5C0VcEocSzKMERi35xguh"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

ALERT_THRESHOLD_USD = 1000   # ✅ LOWERED TO $1K
POLL_INTERVAL = 5

EXCHANGE_ADDRESS = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

# Minimal ABI for Fill event
EXCHANGE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "maker", "type": "address"},
            {"indexed": True, "name": "taker", "type": "address"},
            {"indexed": False, "name": "makerAmount", "type": "uint256"},
            {"indexed": False, "name": "takerAmount", "type": "uint256"},
            {"indexed": False, "name": "fee", "type": "uint256"}
        ],
        "name": "Fill",
        "type": "event"
    }
]

# =========================
# CONNECT
# =========================

w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

exchange_contract = w3.eth.contract(
    address=EXCHANGE_ADDRESS,
    abi=EXCHANGE_ABI
)

print("Connected to Polygon")

# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)

# =========================
# MONITOR
# =========================

def monitor():
    print("🎯 Polymarket $1K+ Trade Monitor Online")
    send_telegram("🚀 $1K+ Polymarket Trade Monitor Started")

    last_block = w3.eth.block_number

    while True:
        try:
            latest_block = w3.eth.block_number

            if latest_block > last_block:

                events = exchange_contract.events.Fill().get_logs(
                    from_block=last_block + 1,
                    to_block=latest_block
                )

                for event in events:

                    maker = event["args"]["maker"]
                    taker = event["args"]["taker"]
                    taker_amount = event["args"]["takerAmount"]

                    # USDC = 6 decimals
                    usdc_amount = taker_amount / 1_000_000

                    # 👀 DEBUG LOG (always prints)
                    print(f"Fill detected: ${usdc_amount:,.2f}")

                    if usdc_amount >= ALERT_THRESHOLD_USD:

                        tx_hash = event["transactionHash"].hex()

                        message = (
                            "🐋 POLYMARKET TRADE ALERT\n\n"
                            f"Size: ${usdc_amount:,.0f}\n"
                            f"Maker: {maker}\n"
                            f"Taker: {taker}\n"
                            f"Block: {event['blockNumber']}\n\n"
                            f"https://polygonscan.com/tx/{tx_hash}"
                        )

                        print("ALERT TRIGGERED")
                        print(message)

                        send_telegram(message)

                last_block = latest_block

            print(f"Alive | Block {latest_block}")
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(10)

# =========================
# KEEP RAILWAY ALIVE
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Polymarket $1K+ Monitor Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
