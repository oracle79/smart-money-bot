import os
import sys
import time
from datetime import datetime, timezone
from web3 import Web3

# =========================
# ENVIRONMENT SETUP
# =========================

RPC = (
    os.getenv("RPC")
    or os.getenv("ALCHEMY_URL")
    or os.getenv("POLYGON_RPC")
)

if not RPC:
    print("❌ ERROR: No RPC variable found.")
    print("Set one of the following in Railway Variables:")
    print("RPC")
    print("ALCHEMY_URL")
    print("POLYGON_RPC")
    sys.exit(1)

if not RPC.startswith("http"):
    print("❌ ERROR: RPC does not look like a valid URL.")
    print("Current value:", RPC)
    sys.exit(1)

print("🔌 Connecting to RPC...")
print("RPC URL:", RPC[:40] + "...")

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    print("❌ ERROR: Could not connect to Polygon RPC.")
    print("Check your Alchemy key.")
    sys.exit(1)

print("✅ Connected to Polygon")
print("📦 Current block:", w3.eth.block_number)

# =========================
# SAFE UTC DATE HANDLING
# =========================

def get_today_utc():
    return str(datetime.now(timezone.utc).date())

state = {
    "last_reset": get_today_utc()
}

print("🧠 Quant Engine Online")
