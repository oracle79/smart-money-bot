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
TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
CHAT_ID = "7154046718"

POLL_INTERVAL = 6
USDC_DECIMALS = 6
ALERT_THRESHOLD = 1000  # $1,000

# Polygon USDC Contract
USDC_ADDRESS = Web3.to_checksum_address(
    "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
)

# Known Polymarket Exchange Contract
POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
)

# ERC20 Transfer event signature
TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()

# =========================
# CONNECT
# =========================

w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

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
# MONITOR USDC TRANSFERS
# =========================

def monitor():
    print("💰 Whale Monitor Online")
    send_telegram("🚀 Polymarket $10k+ Whale Monitor Started")

    last_block = w3.eth.block_number

    while True:
        try:
            latest_block = w3.eth.block_number

            if latest_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": latest_block,
                    "address": USDC_ADDRESS,
                    "topics": [TRANSFER_TOPIC]
                })

                for log in logs:

                    to_address = "0x" + log["topics"][2].hex()[-40:]
                    value = int(log["data"], 16) / (10 ** USDC_DECIMALS)

                    if (
                        Web3.to_checksum_address(to_address) == POLYMARKET_EXCHANGE
                        and value >= ALERT_THRESHOLD
                    ):

                        tx_hash = log["transactionHash"].hex()
                        from_address = "0x" + log["topics"][1].hex()[-40:]

                        message = (
                            "🐋 POLYMARKET WHALE BET DETECTED\n\n"
                            f"Trader: {from_address}\n"
                            f"Amount: ${value:,.0f}\n"
                            f"Block: {log['blockNumber']}\n"
                            f"https://polygonscan.com/tx/{tx_hash}"
                        )

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
    return "Whale Monitor Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
