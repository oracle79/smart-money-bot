import os
import time
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ============================
# ENV VARIABLES
# ============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram variables not set")

# ============================
# WEB3 CONNECTION
# ============================

w3 = Web3(Web3.HTTPProvider(RPC))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon")

print("Connected to Polygon")
print("Current Block:", w3.eth.block_number)

# ============================
# SMART WALLETS (3)
# ============================

SMART_WALLETS = {
    w3.to_checksum_address("0x6d3c5bd13984b2de47c3a88ddc455309aab3d294"),
    w3.to_checksum_address("0xee613b3fc183ee44f9da9c05f53e2da107e3debf"),
    w3.to_checksum_address("0x204f72f35326db932158cba6adff0b9a1da95e14"),
}

print("Tracking Wallets:", len(SMART_WALLETS))

# ============================
# POLYMARKET CONTRACT
# ============================

POLYMARKET_EXCHANGE = w3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

# ============================
# TELEGRAM FUNCTION
# ============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

send_telegram(
    "🧠 Smart Wallet Engine Started\n"
    f"Tracking {len(SMART_WALLETS)} wallets (Polymarket only)"
)

# ============================
# POLYMARKET API FETCH
# ============================

def fetch_market_info(condition_id):
    if not condition_id:
        return None, None, None

    try:
        url = f"https://gamma-api.polymarket.com/markets?conditionId={condition_id}"
        r = requests.get(url, timeout=10)
        data = r.json()

        if isinstance(data, list) and len(data) > 0:
            market = data[0]
            event_name = market.get("question", "Unknown Event")

            prices = market.get("outcomePrices", {})
            yes_price = prices.get("YES")
            no_price = prices.get("NO")

            return event_name, yes_price, no_price

    except Exception as e:
        print("API error:", e)

    return None, None, None

# ============================
# MAIN LOOP
# ============================

last_block = w3.eth.block_number

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:

            for block_num in range(last_block + 1, current_block + 1):

                block = w3.eth.get_block(block_num, full_transactions=True)

                for tx in block.transactions:

                    # Only monitor smart wallets
                    if tx["from"] not in SMART_WALLETS:
                        continue

                    # Only Polymarket exchange
                    if tx["to"] != POLYMARKET_EXCHANGE:
                        continue

                    print("🔥 Polymarket trade detected")

                    tx_hash = tx["hash"].hex()
                    wallet = tx["from"]

                    receipt = w3.eth.get_transaction_receipt(tx_hash)

                    direction = "UNKNOWN"
                    condition_id = None

                    # Basic log scan (placeholder decoding)
                    for log in receipt.logs:
                        if log["address"] == POLYMARKET_EXCHANGE:
                            if len(log["topics"]()
