import time
import threading
import requests
from collections import defaultdict, deque
from flask import Flask
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# =========================
# CONFIG
# =========================

ALCHEMY_URL = "https://polygon-mainnet.g.alchemy.com/v2/5C0VcEocSzKMERi35xguh"

TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
CHAT_ID = "7154046718"

WINDOW_SECONDS = 300
SHARE_THRESHOLD = 500   # LOWERED for testing
POLL_INTERVAL = 4

ZERO = "0x0000000000000000000000000000000000000000"

CTF_ADDRESS = Web3.to_checksum_address(
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
)

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

ctf_contract = w3.eth.contract(address=CTF_ADDRESS, abi=CTF_ABI)

print("Connected to Polygon")
print("🔥 Accumulation Flow Engine Online")

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
# FLOW STORAGE
# =========================

flow_data = defaultdict(lambda: defaultdict(deque))
alerted = set()

# =========================
# MONITOR
# =========================

def monitor():

    send_telegram("🚀 Accumulation Engine Started")

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

                    if from_addr.lower() == ZERO or to_addr.lower() == ZERO:
                        continue

                    token_id = event["args"]["id"]
                    shares = event["args"]["value"] / 1_000_000
                    now = time.time()

                    flow_data[to_addr][token_id].append((now, shares))
                    flow_data[from_addr][token_id].append((now, -shares))

                    for wallet in [to_addr, from_addr]:

                        dq = flow_data[wallet][token_id]

                        while dq and now - dq[0][0] > WINDOW_SECONDS:
                            dq.popleft()

                        net = sum(x[1] for x in dq)
                        key = (wallet, token_id)

                        if abs(net) >= SHARE_THRESHOLD and key not in alerted:

                            direction = "BUYING" if net > 0 else "SELLING"

                            message = (
                                "🔥 ACCUMULATION DETECTED\n\n"
                                f"Wallet: {wallet}\n"
                                f"Direction: {direction}\n"
                                f"Net Shares (5m): {net:,.0f}\n"
                                f"TokenID: {token_id}\n"
                                f"Block: {event['blockNumber']}"
                            )

                            print(message)
                            send_telegram(message)

                            alerted.add(key)

                last_block = latest_block

            print(f"Alive | Block {latest_block}")
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(10)

# =========================
# FLASK
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Accumulation Engine Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
