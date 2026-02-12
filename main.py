import os
import time
import requests
from web3 import Web3
from datetime import datetime

# ==============================
# ENV VARIABLES (DO NOT RENAME)
# ==============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials not set")

# ==============================
# CONNECT TO POLYGON
# ==============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon RPC")

current_block = w3.eth.block_number

print("🧠 Smart Wallet Quant Engine v1 Online")
print("Polygon Block:", current_block)

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
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

send_telegram(f"🧠 Smart Wallet Quant Engine Online\nPolygon Block: {current_block}")

# ==============================
# LEADERBOARD FETCH
# ==============================

def fetch_top_wallets(limit=500):
    print("Fetching weekly leaderboard...")

    try:
        url = "https://gamma-api.polymarket.com/leaderboard"

        params = {
            "period": "7d",
            "limit": limit
        }

        response = requests.get(url, params=params, timeout=20)

        if response.status_code != 200:
            print("Leaderboard request failed:", response.status_code)
            send_telegram("⚠️ Leaderboard request failed")
            return []

        data = response.json()

        wallets = []

        for user in data:
            address = user.get("address")
            pnl = user.get("pnl")

            if address and address.startswith("0x"):
                wallets.append({
                    "address": Web3.to_checksum_address(address),
                    "pnl": pnl
                })

        print("Loaded wallets:", len(wallets))
        send_telegram(f"📊 Tracking {len(wallets)} top weekly wallets")

        return wallets

    except Exception as e:
        print("Leaderboard fetch error:", e)
        send_telegram(f"⚠️ Leaderboard error")
        return []

# ==============================
# SIMPLE WALLET MONITOR LOOP
# ==============================

def monitor_wallets(wallets):

    last_block = w3.eth.block_number

    print("Starting wallet monitor loop...")
    send_telegram("🚀 Wallet monitoring started")

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                print("New block:", current_block)

                # For now we just heartbeat.
                # Real cluster detection comes next phase.
                send_telegram(f"📦 New Polygon Block: {current_block}")

                last_block = current_block

            time.sleep(15)

        except Exception as e:
            print("Monitor error:", e)
            time.sleep(10)

# ==============================
# WEEKLY REFRESH SYSTEM
# ==============================

def run_engine():

    wallets = fetch_top_wallets(limit=500)

    print("Tracking Wallets:", len(wallets))

    if len(wallets) == 0:
        send_telegram("⚠️ No wallets loaded")
    else:
        send_telegram("✅ Smart wallet list loaded")

    monitor_wallets(wallets)

# ==============================
# START ENGINE
# ==============================

run_engine()
