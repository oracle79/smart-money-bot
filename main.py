import os
import time
import requests
from datetime import datetime, timezone
from web3 import Web3
from web3.middleware import geth_poa_middleware

# =========================
# ENV VARIABLES
# =========================

RPC_URL = os.getenv("RPC_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC_URL:
    raise Exception("❌ RPC_URL not set in Railway variables")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("❌ Telegram credentials missing")

# =========================
# TELEGRAM FUNCTION
# =========================

def send_telegram(message: str):
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
# WEB3 CONNECTION
# =========================

print("🔌 Connecting to Polygon RPC...")

w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 30}))

# Inject POA middleware (REQUIRED FOR POLYGON)
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if not w3.is_connected():
    raise Exception("❌ Failed to connect to Polygon RPC")

current_block = w3.eth.block_number

print("✅ Connected to Polygon")
print("📦 Current Block:", current_block)

send_telegram(
    f"🧠 Smart Cluster Quant Engine STABLE\n"
    f"✅ Connected to Polygon\n"
    f"📦 Block: {current_block}\n"
    f"🕒 {datetime.now(timezone.utc)}"
)

# =========================
# MAIN LOOP (STABLE CORE)
# =========================

print("🚀 Engine R
