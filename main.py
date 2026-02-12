import os
import time
import requests
from web3 import Web3
from datetime import datetime, timezone

# ==============================
# LOAD ENV VARIABLES
# ==============================

RPC = os.getenv("RPC")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not RPC:
    raise Exception("RPC not set in Railway variables")

if not TELEGRAM_CHAT_ID:
    raise Exception("TELEGRAM_CHAT_ID not set in Railway variables")

if not TELEGRAM_TOKEN:
    raise Exception("TELEGRAM_TOKEN not set in Railway variables")

# ==============================
# TELEGRAM FUNCTION
# ==============================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code != 200:
            print("Telegram error:", response.text)

    except Exception as e:
        print("Telegram send failed:", str(e))


# ==============================
# CONNECT TO POLYGON
# ==============================

print("🔌 Connecting to RPC...")
print("RPC:", RPC[:40] + "...")

try:
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))

    if not w3.is_connected():
        raise Exception("Web3 connection failed")

    print("✅ Connected to Polygon")

except Exception as e:
    print("❌ RPC CONNECTION FAILED:", str(e))
    raise e


# ==============================
# START ENGINE
# ==============================

current_block = w3.eth.block_number
today = datetime.now(timezone.utc).date()

startup_message = f"""
🧠 Smart Wallet Quant Engine ONLINE

📦 Current Block: {current_block}
📅 Date (UTC): {today}

🚀 Engine Running
"""

print(startup_message)
send_telegram(startup_message)


# ==============================
# HEARTBEAT LOOP
# ==============================

last_block = current_block

while True:
    try:
        block = w3.eth.block_number

        if block != last_block:
            last_block = block

            heartbeat_message = f"""
📦 New Block Detected
Block: {block}
Time: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
"""

            print(heartbeat_message.strip())
            send_telegram(heartbeat_message.strip())

        time.
