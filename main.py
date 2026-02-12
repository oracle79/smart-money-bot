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

ALERT_THRESHOLD_USD = 1000
POLL_INTERVAL = 5

EXCHANGE_ADDRESS = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

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
# EVENT SIGNATURE
# =========================

# Fill event signature
FILL_TOPIC = Web3.keccak(
    text="Fill(address,address,address,uint256,uint256,uint256,uint256)"
).hex()

# =========================
# MONITOR
# =========================

def monitor():
    print("🎯 Polymarket Whale Trade Monitor Online")
    send_telegram("🚀 $10k+ Polymarket Trade Monitor Started")

    last_block = w3.eth.block_number

    while True:
        try:
            latest_block = w3.eth.block_number

            if latest_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": latest_block,
                    "address": EXCHANGE_ADDRESS,
                    "topics": [FILL_TOPIC]
                })

                for log in logs:

                    tx_hash = log["transactionHash"].hex()

                    # Decode raw values from data
                    data = log["data"]

                    # Each uint256 is 32 bytes
                    values = [
                        int(data[i:i+64], 16)
                        for i in range(2, len(data), 64)
                    ]

                    # Polymarket Fill event structure:
                    # values[0] = makerAmount
                    # values[1] = takerAmount
                    # (USDC is 6 decimals)

                    if len(values) >= 2:
                        usdc_amount = values[1] / 1_000_000

                        if usdc_amount >= ALERT_THRESHOLD_USD:

                            message = (
                                "🐋 POLYMARKET WHALE TRADE\n\n"
                                f"Size: ${usdc_amount:,.0f}\n"
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
    return "Polymarket Whale Monitor Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
