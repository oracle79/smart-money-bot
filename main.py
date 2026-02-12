import time
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# =============================
# CONFIG
# =============================

RPC_URL = "https://polygon-rpc.com"

TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
CHAT_ID = "7154046718"

SMART_WALLETS = [
    "0x6d3c5bd13984b2de47c3a88ddc455309aab3d294",
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf",
    "0x204f72f35326db932158cba6adff0b9a1da95e14"
]

POLYMARKET_EXCHANGE = Web3.to_checksum_address("0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e")

MIN_USD_THRESHOLD = 1  # for testing

# =============================
# WEB3 SETUP
# =============================

w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

print("🧠 Smart Wallet Engine Online")
print("Tracking", len(SMART_WALLETS), "wallets")

# =============================
# TELEGRAM
# =============================

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# =============================
# FETCH EVENT DATA
# =============================

def fetch_market_data(token_id):
    try:
        url = "https://gamma-api.polymarket.com/markets"
        response = requests.get(url, timeout=10)
        markets = response.json()

        for market in markets:
            if str(token_id).lower() in str(market).lower():
                event_name = market.get("question", "Unknown Event")
                yes_price = market.get("outcomePrices", [0,0])[0]
                no_price = market.get("outcomePrices", [0,0])[1]
                return event_name, yes_price, no_price

    except:
        pass

    return "Unknown Event", "?", "?"

# =============================
# MONITOR LOOP
# =============================

last_block = w3.eth.block_number

while True:
    try:
        current_block = w3.eth.block_number

        for block_num in range(last_block + 1, current_block + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)

            for tx in block.transactions:
                if tx["from"] and tx["from"].lower() in [w.lower() for w in SMART_WALLETS]:

                    if tx["to"] and tx["to"].lower() == POLYMARKET_EXCHANGE.lower():

                        value_usd = w3.from_wei(tx["value"], "ether")

                        if value_usd >= MIN_USD_THRESHOLD:

                            token_id = tx["input"][:10]  # placeholder decode

                            event_name, yes_price, no_price = fetch_market_data(token_id)

                            direction = "YES/NO (decoded soon)"

                            message = f"""
🚨 Smart Wallet Trade Detected

Wallet: {tx['from']}
Event: {event_name}

Direction: {direction}
Amount: ${round(float(value_usd),2)}

Current Prices:
YES: {yes_price}
NO: {no_price}
"""
                            print(message)
                            send_telegram(message)

        last_block = current_block
        print("Alive | Block", current_block)
        time.sleep(5)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)
