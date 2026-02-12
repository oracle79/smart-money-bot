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

ALERT_THRESHOLD = 1000  # $1,000+
POLL_INTERVAL = 4

CTF_ADDRESS = Web3.to_checksum_address(
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
)

# ERC1155 TransferSingle ABI
CTF_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "operator", "type": "address"},
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "id", "type": "uint256"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "TransferSingle",
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

ctf_contract = w3.eth.contract(
    address=CTF_ADDRESS,
    abi=CTF_ABI
)

print("Connected to Polygon")
print(f"Monitoring CTF contract: {CTF_ADDRESS}")

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
    print("🎯 Polymarket ERC1155 Monitor Online")
    send_telegram("🚀 Polymarket ERC1155 Monitor Started")

    last_block = w3.eth.block_number

    while True:
        try:
            latest_block = w3.eth.block_number

            if latest_block > last_block:

                events = ctf_contract.events.TransferSingle().get_logs(
                    from_block=last_block + 1,
                    to_block=latest_block
                )

                for event in events:

                    from_addr = event["args"]["from"]
                    to_addr = event["args"]["to"]
                    token_id = event["args"]["id"]
                    raw_value = event["args"]["value"]

                    # Polymarket positions use 6 decimals
                    shares = raw_value / 1_000_000

                    print(
                        f"Transfer detected | Shares: {shares:.2f} | "
                        f"From: {from_addr} | To: {to_addr}"
                    )

                    if shares >= ALERT_THRESHOLD:

                        tx_hash = event["transactionHash"].hex()

                        message = (
                            "🔥 POLYMARKET LARGE POSITION TRANSFER\n\n"
                            f"Shares: {shares:,.0f}\n"
                            f"From: {from_addr}\n"
                            f"To: {to_addr}\n"
                            f"TokenID: {token_id}\n"
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
    return "Polymarket ERC1155 Monitor Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
