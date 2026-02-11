from web3 import Web3
import os
import time
import requests
import random
from datetime import datetime, timedelta, timezone

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# ==============================
# BASIC SETTINGS
# ==============================
STARTING_CAPITAL = 1000
capital = STARTING_CAPITAL

MAX_RISK_PER_TRADE = 0.02          # 2% max risk
MAX_DAILY_LOSS = 0.05              # 5% daily stop
CLUSTER_WINDOW_SECONDS = 300       # 5 minutes
MIN_TRADE_SIZE = 100               # $100 minimum
MIN_WALLETS_FOR_CLUSTER = 3

daily_loss = 0
last_reset_day = datetime.now(timezone.utc).date()

# ==============================
# CONNECT TO POLYGON
# ==============================
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"

# ==============================
# TELEGRAM FUNCTION
# ==============================
def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram not configured")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ==============================
# LOAD SMART WALLETS
# ==============================
def load_smart_wallets():
    wallets = set()
    try:
        with open("smart_wallets.txt", "r") as f:
            for line in f:
                wallets.add(line.strip().lower())
    except:
        print("No smart_wallets.txt found — using empty set")
    return wallets

smart_wallets = load_smart_wallets()
print(f"Loaded {len(smart_wallets)} smart wallets")

# ==============================
# TRADE MEMORY FOR CLUSTERING
# ==============================
recent_trades = []

# ==============================
# SAFE SIZE CALCULATION
# ==============================
def calculate_position_size():
    return capital * MAX_RISK_PER_TRADE

# ==============================
# DAILY RESET
# ==============================
def check_daily_reset():
    global daily_loss, last_reset_day
    today = datetime.now(timezone.utc).date()
    if today != last_reset_day:
        daily_loss = 0
        last_reset_day = today

# ==============================
# PAPER TRADE EXECUTION
# ==============================
def execute_paper_trade():
    global capital, daily_loss

    if daily_loss >= STARTING_CAPITAL * MAX_DAILY_LOSS:
        print("Daily loss limit reached. Trading halted.")
        return

    position_size = calculate_position_size()

    # Simulated 55% win probability (temporary until real edge measured)
    if random.random() < 0.55:
        profit = position_size * 1.0
        capital += profit
        send_telegram(f"📈 PAPER WIN +${profit:.2f} | Capital: ${capital:.2f}")
    else:
        loss = position_size
        capital -= loss
        daily_loss += loss
        send_telegram(f"📉 PAPER LOSS -${loss:.2f} | Capital: ${capital:.2f}")

# ==============================
# CLUSTER CHECK
# ==============================
def check_cluster():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=CLUSTER_WINDOW_SECONDS)

    valid_trades = [t for t in recent_trades if t["time"] > cutoff]

    if len(valid_trades) >= MIN_WALLETS_FOR_CLUSTER:
        send_telegram(
            f"🚨 CLUSTER DETECTED\n"
            f"Wallets: {len(valid_trades)}\n"
            f"Capital: ${capital:.2f}"
        )
        execute_paper_trade()

# ==============================
# MAIN LOOP
# ==============================
if __name__ == "__main__":

    if not w3.is_connected():
        print("Polygon connection failed")
        send_telegram("❌ Polygon connection failed")
        exit()

    send_telegram("🚀 Paper Trading Engine Started")

    last_block = w3.eth.block_number

    while True:
        try:
            check_daily_reset()

            current_block = w3.eth.block_number

            if current_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": POLYMARKET_EXCHANGE,
                    "topics": [FILL_TOPIC]
                })

                for log in logs:

                    topics = [t.hex() for t in log["topics"]]

                    if len(topics) < 4:
                        continue

                    maker = "0x" + topics[2][-40:]
                    taker = "0x" + topics[3][-40:]

                    # Simulated trade size (replace with real decoding later)
                    trade_size = random.uniform(50, 500)

                    if trade_size < MIN_TRADE_SIZE:
                        continue

                    if maker.lower() in smart_wallets or taker.lower() in smart_wallets:

                        tx_hash = log["transactionHash"].hex()

                        send_telegram(
                            f"🚨 SMART WALLET TRADE\n"
                            f"Maker: {maker}\n"
                            f"Taker: {taker}\n"
                            f"Size: ${trade_size:.2f}\n"
                            f"https://polygonscan.com/tx/{tx_hash}"
                        )

                        recent_trades.append({
                            "time": datetime.now(timezone.utc)
                        })

                        check_cluster()

                last_block = current_block

            time.sleep(3)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
