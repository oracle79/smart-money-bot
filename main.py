import os
import time
from web3 import Web3
import requests

# ==============================
# ENVIRONMENT VARIABLES
# ==============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set in Railway variables")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# ==============================
# WEB3 CONNECTION
# ==============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Web3 failed to connect")

print("✅ Connected to Polygon")

# ==============================
# POLYMARKET EXCHANGE CONTRACT
# ==============================

EXCHANGE_ADDRESS = Web3.to_checksum_address(
    "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
)

ABI = [{"inputs":[{"internalType":"address","name":"_collateral","type":"address"},{"internalType":"address","name":"_ctf","type":"address"},{"internalType":"address","name":"_proxyFactory","type":"address"},{"internalType":"address","name":"_safeFactory","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"orderHash","type":"bytes32"},{"indexed":true,"internalType":"address","name":"maker","type":"address"},{"indexed":true,"internalType":"address","name":"taker","type":"address"},{"indexed":false,"internalType":"uint256","name":"makerAssetId","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"takerAssetId","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"makerAmountFilled","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"takerAmountFilled","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"fee","type":"uint256"}],"name":"OrderFilled","type":"event"}]

exchange = w3.eth.contract(address=EXCHANGE_ADDRESS, abi=ABI)
order_filled_event = exchange.events.OrderFilled()

# ==============================
# TELEGRAM FUNCTION
# ==============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# PROCESS LOG
# ==============================

def process_log(log):
    try:
        decoded = order_filled_event.process_log(log)
        args = decoded["args"]

        maker = args["maker"]
        taker = args["taker"]
        maker_asset = args["makerAssetId"]
        taker_asset = args["takerAssetId"]
        maker_amount = args["makerAmountFilled"]
        taker_amount = args["takerAmountFilled"]
        fee = args["fee"]

        if maker_amount == 0:
            return

        price = taker_amount / maker_amount

        message = f"""
🚨 Polymarket Trade Detected

Maker: {maker}
Taker: {taker}

Maker Asset ID: {maker_asset}
Taker Asset ID: {taker_asset}

Maker Amount: {maker_amount}
Taker Amount: {taker_amount}

Implied Price: {round(price, 6)}
Fee: {fee}
        """

        print(message)
        send_telegram(message)

    except Exception as e:
        print("Decode error:", e)

# ==============================
# MAIN LOOP
# ==============================

def main():
    print("🎯 Listening for OrderFilled events...")

    event_signature = w3.keccak(
        text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
    ).hex()

    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": EXCHANGE_ADDRESS,
                    "topics": [event_signature]
                })

                for log in logs:
                    process_log(log)

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Main loop error:", e)
            time.sleep(5)

# ==============================
# START
# ==============================

if __name__ == "__main__":
    main()
