import os
import time
import requests
from web3 import Web3

# =========================
# ENV VARIABLES
# =========================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# =========================
# CONNECT WEB3
# =========================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon RPC")

print("🧠 Smart Wallet Quant Engine Online")
print("Polygon Block:", w3.eth.block_number)

# =========================
# TELEGRAM FUNCTION
# =========================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# =========================
# FETCH WEEKLY LEADERBOARD
# =========================

def fetch_top_wallets(limit=500):
    print("Fetching weekly leaderboard...")

    try:
        # Gamma API endpoint used by frontend
        url = "https://gamma-api.polymarket.com/users"
        params = {
            "limit": limit,
            "sort": "pnl_7d",
            "order": "desc"
        }

        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()

        wallets = []

        for user in data:
            address = user.get("address")
            pnl = user.get("pnl_7d")

            if address:
                wallets.append({
                    "address": Web3.to_checksum_address(address),
                    "pnl": pnl
                })

        print(f"Loaded {len(wallets)} smart wallets")

        send_telegram(f"🧠 Tracking {len(wallets)} top weekly wallets")

        return wallets

    except Exception as e:
        print("Leaderboard fetch error:", e)
        send_telegram("⚠️ Failed to fetch leaderboard")
        return []

# =========================
# CONTRACT SETTINGS
# =========================

CTF_EXCHANGE = Web3.to_checksum_address("0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E")

# =========================
# MONITOR FUNCTION
# =========================

def monitor(wallets):
    print("Monitoring smart wallets...")

    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": CTF_EXCHANGE
                })

                for log in logs:
                    if log["topics"]:
                        wallet = "0x" + log["topics"][1].hex()[-40:]

                        if wallet in [w["address"] for w in wallets]:
                            message = f"🔥 Smart Wallet Trade Detected\nWallet: {wallet}\nBlock: {log['blockNumber']}"
                            print(message)
                            send_telegram(message)

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Monitor error:", e)
            time.sleep(5)

# =========================
# RUN ENGINE
# =========================

SMART_WALLETS = fetch_top_wallets(500)

if SMART_WALLETS:
    monitor(SMART_WALLETS)
else:
    print("No wallets loaded. Engine idle.")
