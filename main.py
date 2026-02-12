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
SHARE_THRESHOLD = 1000
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

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

ctf_contract = w3.eth.contract(address=CTF_ADDRESS, abi=CTF_ABI)

print("Connected to Polygon")
print("🧠 Polymarket Intelligence Engine Online")

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
# SAFE MARKET FETCH
# =========================

def fetch_market_data(condition_id):
    try:
        url = f"https://gamma-api.polymarket.com/markets?conditionId={condition_id}"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()

        # Must be list
        if not isinstance(data, list):
            return None

        if len(data) == 0:
            return None

        market = data[0]

        outcomes = market.get("outcomes")

        if not isinstance(outcomes, list) or len(outcomes) < 2:
            return None

        yes_price = float(outcomes[0].get("price", 0))
        no_price = float(outcomes[1].get("price", 0))

        return {
            "question": market.get("question", "Unknown Market"),
            "yes_price": yes_price,
            "no_price": no_price
        }

    except Exception:
        return None

# =========================
# FLOW STORAGE
# =========================

flow_data = defaultdict(lambda: defaultdict(deque))
alerted = set()

# =========================
# TOKEN DECODER
# =========================

def decode_token(token_id):
    outcome_index = token_id & 1
    condition_id = hex(token_id >> 1)
    return condition_id, outcome_index

# =========================
# MONITOR
# =========================

def monitor():

    send_telegram("🚀 Polymarket Intelligence Engine Started")

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

                            condition_id, outcome_index = decode_token(token_id)
                            market = fetch_market_data(condition_id)

                            if market:

                                price = (
                                    market["yes_price"]
                                    if outcome_index == 0
                                    else market["no_price"]
                                )

                                usd_value = abs(net) * price
                                direction = "BUYING" if net > 0 else "SELLING"
                                side = "YES" if outcome_index == 0 else "NO"

                                message = (
                                    "🔥 SMART FLOW DETECTED\n\n"
                                    f"Wallet: {wallet}\n"
                                    f"Direction: {direction}\n"
                                    f"Side: {side}\n"
                                    f"Net Shares (5m): {net:,.0f}\n"
                                    f"USD Value: ${usd_value:,.0f}\n\n"
                                    f"Market: {market['question']}\n"
                                    f"YES Price: {market['yes_price']}\n"
                                    f"NO Price: {market['no_price']}\n"
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
# FLASK (Railway Keep Alive)
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Polymarket Intelligence Engine Running"

threading.Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
