import time
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ==============================
# CONFIG
# ==============================

RPC_URL = "https://polygon-rpc.com"

TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
CHAT_ID = "7154046718"

SMART_WALLETS = [
    Web3.to_checksum_address("0x6d3c5bd13984b2de47c3a88ddc455309aab3d294"),
    Web3.to_checksum_address("0xee613b3fc183ee44f9da9c05f53e2da107e3debf"),
    Web3.to_checksum_address("0x204f72f35326db932158cba6adff0b9a1da95e14")
]

MIN_USD_THRESHOLD = 1  # testing threshold

# ==============================
# WEB3 SETUP
# ==============================

w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise Exception("RPC connection failed")

print("🧠 Smart Wallet Engine Online")
print("Tracking", len(SMART_WALLETS), "wallets")

# ==============================
# TELEGRAM FUNCTION
# ==============================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# POLLING ENGINE (LOW RPC MODE)
# ==============================

last_block = w3.eth.block_number
print("Starting from block:", last_block)

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:

            # Only fetch block headers (NO full tx objects)
            block = w3.eth.get_block(current_block, full_transactions=False)

            for tx_hash in block.transactions:

                tx = w3.eth.get_transaction(tx_hash)

                if tx["from"] in SMART_WALLETS:

                    value_usd = w3.from_wei(tx["value"], "ether")

                    if float(value_usd) >= MIN_USD_THRESHOLD:

                        message = (
                            "🚨 Smart Wallet Activity\n\n"
                            f"Wallet: {tx['from']}\n"
                            f"Block: {current_block}\n"
                            f"Value: ${round(float(value_usd), 2)}\n"
                            f"Tx: https://polygonscan.com/tx/{tx_hash.hex()}"
                        )

                        print(message)
                        send_telegram(message)

            last_block = current_block
            print("Alive | Block", current_block)

        time.sleep(12)  # slower polling to avoid rate limits

    except Exception as e:
        print("Loop error:", e)
        time.sleep(15)
