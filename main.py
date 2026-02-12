import os
import time
import requests
from datetime import datetime, timedelta
from web3 import Web3
from collections import defaultdict

# ==============================
# ENV VARIABLES
# ==============================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram variables missing")

# ==============================
# WEB3 CONNECTION
# ==============================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Failed to connect to Polygon RPC")

print("🧠 Smart Wallet Cluster Engine Online")
print("Polygon Block:", w3.eth.block_number)

# ==============================
# TELEGRAM
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
# CONFIG
# ==============================

USDC_ADDRESS = Web3.to_checksum_address(
    "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
)

USDC_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "from", "type": "address"},
        {"indexed": True, "name": "to", "type": "address"},
        {"indexed": False, "name": "value", "type": "uint256"},
    ],
    "name": "Transfer",
    "type": "event",
}]

usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)

TOP_WALLETS = {}
TRADE_LOG = defaultdict(list)

CLUSTER_THRESHOLD = 3
CLUSTER_WINDOW_MINUTES = 60
CONVICTION_THRESHOLD = 0.25
LARGE_TRADE_USD = 1000

HEARTBEAT_INTERVAL = 600  # 10 minutes

# ==============================
# LEADERBOARD FETCH
# ==============================

def fetch_top_wallets():
    global TOP_WALLETS

    print("🔄 Fetching leaderboard...")

    try:
        url = "https://gamma-api.polymarket.com/leaderboard?period=weekly"
        response = requests.get(url, timeout=10)
        data = response.json()

        wallets = {}

        for entry in data[:500]:
            wallet = entry.get("address")
            pnl = float(entry.get("profit", 0))
            volume = float(entry.get("volume", 0))

            if wallet:
                wallets[wallet.lower()] = {
                    "pnl": pnl,
                    "volume": volume,
                    "est_bankroll": max(pnl * 3, 1000)
                }

        TOP_WALLETS = wallets

        wallet_count = len(TOP_WALLETS)

        print(f"✅ Wallets fetched: {wallet_count}")

        send_telegram(
            f"📊 Leaderboard Loaded\n"
            f"Wallets Tracked: {wallet_count}\n"
            f"Block: {w3.eth.block_number}"
        )

    except Exception as e:
        print("❌ Failed to fetch leaderboard:", e)
        send_telegram("❌ Failed to fetch leaderboard")

# ==============================
# CLUSTER DETECTION
# ==============================

def check_cluster(wallet, direction, market, timestamp):

    TRADE_LOG[market].append((wallet, direction, timestamp))

    cutoff = datetime.utcnow() - timedelta(minutes=CLUSTER_WINDOW_MINUTES)

    recent = [
        t for t in TRADE_LOG[market]
        if t[2] > cutoff
    ]

    yes_wallets = set([t[0] for t in recent if t[1] == "YES"])
    no_wallets = set([t[0] for t in recent if t[1] == "NO"])

    if len(yes_wallets) >= CLUSTER_THRESHOLD:
        send_telegram(
            f"🔥 CLUSTER DETECTED (YES)\n"
            f"Market: {market}\n"
            f"Wallets: {len(yes_wallets)}"
        )

    if len(no_wallets) >= CLUSTER_THRESHOLD:
        send_telegram(
            f"🔥 CLUSTER DETECTED (NO)\n"
            f"Market: {market}\n"
            f"Wallets: {len(no_wallets)}"
        )

# ==============================
# MONITOR LOOP
# ==============================

def monitor():

    last_block = w3.eth.block_number
    last_heartbeat = time.time()

    transfer_event = usdc_contract.events.Transfer()

    send_telegram("🚀 Wallet Monitoring Started")

    while True:
        try:
            current_block = w3.eth.block_number

            # Heartbeat every 10 min
            if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                send_telegram(
                    f"💓 Engine Alive\n"
                    f"Block: {current_block}\n"
                    f"Wallets Monitoring: {len(TOP_WALLETS)}"
                )
                last_heartbeat = time.time()

            if current_block > last_block:

                logs = transfer_event.get_logs(
                    fromBlock=last_block,
                    toBlock=current_block
                )

                for log in logs:

                    from_addr = log["args"]["from"].lower()
                    value = log["args"]["value"] / 1_000_000
                    tx_hash = log["transactionHash"].hex()

                    if from_addr in TOP_WALLETS and value >= LARGE_TRADE_USD:

                        bankroll = TOP_WALLETS[from_addr]["est_bankroll"]
                        conviction = value / bankroll

                        direction = "YES"  # placeholder
                        market = tx_hash[:10]  # placeholder
                        timestamp = datetime.utcnow()

                        send_telegram(
                            f"🚨 LARGE TRADE\n"
                            f"Wallet: {from_addr}\n"
                            f"Size: ${value:,.0f}\n"
                            f"Block: {current_block}\n"
                            f"Tx: https://polygonscan.com/tx/{tx_hash}"
                        )

                        if conviction >= CONVICTION_THRESHOLD:
                            send_telegram(
                                f"💰 HIGH CONVICTION\n"
                                f"Wallet: {from_addr}\n"
                                f"{conviction:.0%} of est bankroll"
                            )

                        check_cluster(from_addr, direction, market, timestamp)

                last_block = current_block

            time.sleep(8)

        except Exception as e:
            print("Monitor error:", e)
            time.sleep(5)

# ==============================
# START ENGINE
# ==============================

fetch_top_wallets()
monitor()
