import os
import sys
import requests
from datetime import datetime, timezone
from web3 import Web3

print("🚀 Booting Quant Engine...")

# =========================
# ENV VARIABLES
# =========================

RPC = (
    os.getenv("RPC")
    or os.getenv("ALCHEMY_URL")
    or os.getenv("POLYGON_RPC")
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================
# VALIDATION
# =========================

if not RPC:
    print("❌ RPC variable not set.")
    print("Set RPC in Railway Variables.")
    sys.exit(1)

if not RPC.startswith("http"):
    print("❌ RPC does not look valid.")
    print("Current value:", RPC)
    sys.exit(1)

print("🔌 Connecting to Polygon RPC...")
print("RPC:", RPC[:45] + "...")

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    print("❌ Could not connect to RPC.")
    print("Your Alchemy key is likely invalid.")
    sys.exit(1)

print("✅ Connected to Polygon")
print("📦 Current Block:", w3.eth.block_number)

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Telegram credentials missing.")
    print("Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in Railway.")
    sys.exit(1)

print("✅ Telegram variables found.")

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
        print("Telegram send error:", e)

# =========================
# ENGINE START
# =========================

def get_today_utc():
    return str(datetime.now(timezone.utc).date())

print("🧠 Quant Engine Online")
print("📅 Date:", get_today_utc())

send_telegram("✅ Quant Engine is ONLINE\nConnected to Polygon\nBlock: " + str(w3.eth.block_number))

# Keep container alive
while True:
    pass
