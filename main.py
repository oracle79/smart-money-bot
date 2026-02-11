from web3 import Web3
import os
import time
import requests

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# ==============================
# POLYMARKET LEADERBOARD CONFIG
# ==============================
LEADERBOARD_API = "https://data-api.polymarket.com/v1/leaderboard"
TIME_PERIOD = "WEEK"
LIMIT = 500

# ==============================
# CONNECT TO POLYGON
# ==============================
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"

MIN_USDC_SIZE = 100  # 🔥 Changed from 2000 to 100

# ==============================
# TELEGRAM FUNCTION
# ==============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# FETCH SMART WALLETS
# ==============================

def fetch_smart_wallets():
    params = {
        "timePeriod": TIME_PERIOD,
        "orderBy": "PNL",
        "limit": LIMIT
    }

    try:
        response = requests.get(LEADERBOARD_API, params=params, timeout=10)
        data = response.json()
    except Exception as e:
        print("❌ Leaderboard fetch error:", e)
        return set()

    wallets = set()

    for trader in data:
        wallet = trader.get("proxyWallet")
        if wallet:
            wallets.add(wallet.lower())

    print(f"✅ Loaded {len(wallets)} smart wallets")
    return wallets

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    if not w3.is_connected():
        print("❌ Polygon connection failed")
        send_telegram("❌ Polygon connection failed")
        exit()

    print("✅ Connected to Polygon")
    send_telegram("🚀 Smart Wallet Monitor Starting...")

    SMART_WALLETS = fetch_smart_wallets()

    if len(SMART_WALLETS) == 0:
        send_telegram("⚠️ Failed to load smart wallets")
        exit()

    send_telegram(f"✅ Loaded {len(SMART_WALLETS)} smart wallets")

    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": POLYMARKET_EXCHANGE,
                    "topics": [FILL_TOPIC]
                })

                for log in logs:

                    tx_hash = log["transactionHash"].hex()
                    topics = [t.hex() for t in log["topics"]]

                    maker = "0x" + topics[2][-40:]
                    taker = "0x" + topics[3][-40:]

                    data_hex = log["data"].hex()
                    chunks = [data_hex[i:i+64] for i in range(0, len(data_hex), 64)]

                    if len(chunks) < 4:
                        continue

                    raw_amount = int(chunks[3], 16)
                    usdc_amount = raw_amount / 1_000_000

                    if taker.lower() not in SMART_WALLETS:
                        continue

                    if usdc_amount < MIN_USDC_SIZE:
                        continue

                    message = (
                        f"🚨 SMART WALLET TRADE\n\n"
                        f"Taker: {taker}\n"
                        f"Maker: {maker}\n\n"
                        f"Size: ${usdc_amount:,.2f}\n\n"
                        f"Tx:\nhttps://polygonscan.com/tx/{tx_hash}"
                    )

                    print(message)
                    send_telegram(message)

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
