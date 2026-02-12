import os
import time
import requests
from web3 import Web3

# =============================
# ENV VARIABLES
# =============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =============================
# CONNECT WEB3
# =============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Web3 failed to connect")

print("🧠 Smart Wallet Quant Engine Online")
print("Polygon Block:", w3.eth.block_number)

# =============================
# POLYMARKET EXCHANGE CONTRACT
# =============================

EXCHANGE_ADDRESS = Web3.to_checksum_address(
    "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
)

# =============================
# TELEGRAM FUNCTION
# =============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# =============================
# START MESSAGE
# =============================

send_telegram(
    f"🧠 Quant Engine Live\n"
    f"Block: {w3.eth.block_number}\n"
    f"Monitoring large trades > $1,000"
)

# =============================
# LARGE TRADE MONITOR
# =============================

MIN_USDC_SIZE = 1000  # $1,000 threshold
last_block = w3.eth.block_number

while True:
    try:
        current_block = w3.eth.block_number

        if current_block > last_block:

            logs = w3.eth.get_logs({
                "fromBlock": last_block + 1,
                "toBlock": current_block,
                "address": EXCHANGE_ADDRESS
            })

            for log in logs:
                tx = w3.eth.get_transaction(log["transactionHash"])
                wallet = tx["from"]

                # crude size estimation from tx value or input length
                # (proper decode will come next phase)
                tx_value = w3.from_wei(tx["value"], "ether")

                # Polymarket trades usually use USDC via contract,
                # so tx.value is 0 — so we use gas usage proxy for now

                receipt = w3.eth.get_transaction_receipt(log["transactionHash"])
                gas_used = receipt["gasUsed"]

                # crude size proxy (temporary)
                # will replace with full decoding later
                estimated_size = gas_used / 100  # placeholder heuristic

                if estimated_size >= MIN_USDC_SIZE:

                    message = (
                        "🚨 LARGE TRADE DETECTED\n\n"
                        f"Wallet: {wallet}\n"
                        f"Estimated Size: ${int(estimated_size)}+\n"
                        f"Block: {current_block}\n"
                        f"Tx: https://polygonscan.com/tx/{log['transactionHash'].hex()}"
                    )

                    send_telegram(message)

            last_block = current_block

        time.sleep(3)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)
