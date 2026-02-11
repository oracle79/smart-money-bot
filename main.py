import os
import time
import json
import csv
import requests
from web3 import Web3
from datetime import datetime, timedelta
from collections import defaultdict
import math

# =========================
# ENV
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# =========================
# SETTINGS
# =========================
STARTING_CAPITAL = 1000
MAX_DAILY_LOSS = 0.07
MAX_RISK_PER_TRADE = 0.05
KELLY_FRACTION = 0.25

CLUSTER_WINDOW_MINUTES = 60
CLUSTER_THRESHOLD = 3
EVALUATION_DELAY_MINUTES = 30

DATA_FOLDER = "data"
SMART_WALLETS_FILE = f"{DATA_FOLDER}/smart_wallets.json"
WALLET_SCORES_FILE = f"{DATA_FOLDER}/wallet_scores.json"
OPEN_CLUSTERS_FILE = f"{DATA_FOLDER}/open_clusters.json"
PERFORMANCE_LOG_FILE = f"{DATA_FOLDER}/performance_log.csv"
RISK_STATE_FILE = f"{DATA_FOLDER}/risk_state.json"

POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"

# =========================
# SETUP
# =========================
os.makedirs(DATA_FOLDER, exist_ok=True)
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

def send_telegram(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message}
        )
    except:
        pass

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# =========================
# STATE
# =========================
smart_wallets = set(load_json(SMART_WALLETS_FILE, []))
wallet_scores = load_json(WALLET_SCORES_FILE, {})
open_clusters = load_json(OPEN_CLUSTERS_FILE, [])
risk_state = load_json(RISK_STATE_FILE, {
    "capital": STARTING_CAPITAL,
    "daily_pnl": 0,
    "last_reset": str(datetime.utcnow().date())
})

recent_trades = defaultdict(list)

# =========================
# PRICE FETCH
# =========================
def get_market_price(market_id):
    try:
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        r = requests.get(url)
        data = r.json()
        return float(data["lastTradePrice"])
    except:
        return None

# =========================
# RISK
# =========================
def reset_daily_if_needed():
    today = str(datetime.utcnow().date())
    if risk_state["last_reset"] != today:
        risk_state["daily_pnl"] = 0
        risk_state["last_reset"] = today
        save_json(RISK_STATE_FILE, risk_state)

def can_trade():
    if risk_state["daily_pnl"] <= -STARTING_CAPITAL * MAX_DAILY_LOSS:
        return False
    return True

def kelly_position_size(edge):
    if edge <= 0:
        return 0
    kelly = edge
    size = risk_state["capital"] * kelly * KELLY_FRACTION
    cap = risk_state["capital"] * MAX_RISK_PER_TRADE
    return min(size, cap)

# =========================
# WALLET SCORE UPDATE
# =========================
def update_wallet_score(wallet, pnl):
    stats = wallet_scores.get(wallet, {"trades": 0, "pnl": 0})
    stats["trades"] += 1
    stats["pnl"] += pnl
    wallet_scores[wallet] = stats
    save_json(WALLET_SCORES_FILE, wallet_scores)

# =========================
# PERFORMANCE LOG
# =========================
def log_performance(cluster, pnl):
    file_exists = os.path.exists(PERFORMANCE_LOG_FILE)
    with open(PERFORMANCE_LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "time", "market", "direction",
                "entry_price", "exit_price",
                "wallets", "pnl"
            ])
        writer.writerow([
            datetime.utcnow(),
            cluster["market"],
            cluster["direction"],
            cluster["entry_price"],
            cluster["exit_price"],
            len(cluster["wallets"]),
            pnl
        ])

# =========================
# CLUSTER EVALUATION
# =========================
def evaluate_clusters():
    global open_clusters

    updated_clusters = []

    for cluster in open_clusters:

        open_time = datetime.fromisoformat(cluster["time"])
        if datetime.utcnow() - open_time < timedelta(minutes=EVALUATION_DELAY_MINUTES):
            updated_clusters.append(cluster)
            continue

        exit_price = get_market_price(cluster["market"])
        if exit_price is None:
            updated_clusters.append(cluster)
            continue

        entry_price = cluster["entry_price"]
        direction = cluster["direction"]

        if direction == "YES":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        edge = pnl_pct
        size = cluster["size"]
        pnl = size * pnl_pct

        risk_state["capital"] += pnl
        risk_state["daily_pnl"] += pnl

        cluster["exit_price"] = exit_price

        for wallet in cluster["wallets"]:
            update_wallet_score(wallet, pnl)

        log_performance(cluster, pnl)

        send_telegram(
            f"📊 Cluster Result\n"
            f"Market: {cluster['market']}\n"
            f"PnL: ${round(pnl,2)}\n"
            f"Capital: ${round(risk_state['capital'],2)}"
        )

    open_clusters = updated_clusters
    save_json(OPEN_CLUSTERS_FILE, open_clusters)
    save_json(RISK_STATE_FILE, risk_state)

# =========================
# MAIN LOOP
# =========================
if __name__ == "__main__":

    if not w3.is_connected():
        send_telegram("❌ Polygon connection failed")
        exit()

    send_telegram("🚀 Self-Learning Quant Engine Online")

    last_block = w3.eth.block_number

    while True:
        try:
            reset_daily_if_needed()
            evaluate_clusters()

            current_block = w3.eth.block_number

            if current_block > last_block:

                logs = w3.eth.get_logs({
                    "fromBlock": last_block + 1,
                    "toBlock": current_block,
                    "address": POLYMARKET_EXCHANGE,
                    "topics": [FILL_TOPIC]
                })

                for log in logs:

                    # PLACEHOLDER UNTIL FULL DECODE
                    market_id = "GLOBAL"
                    direction = "YES"

                    price = get_market_price(market_id)
                    if price is None:
                        continue

                    wallets = ["example_wallet"]

                    recent_trades[market_id].append({
                        "wallets": wallets,
                        "time": datetime.utcnow()
                    })

                last_block = current_block

            for market, trades in list(recent_trades.items()):

                cutoff = datetime.utcnow() - timedelta(minutes=CLUSTER_WINDOW_MINUTES)
                trades = [t for t in trades if t["time"] > cutoff]
                recent_trades[market] = trades

                unique_wallets = set()
                for t in trades:
                    for w in t["wallets"]:
                        unique_wallets.add(w)

                if len(unique_wallets) >= CLUSTER_THRESHOLD and can_trade():

                    edge = 0.05  # will become real measured edge soon
                    size = kelly_position_size(edge)

                    entry_price = get_market_price(market)
                    if entry_price is None:
                        continue

                    cluster = {
                        "market": market,
                        "direction": direction,
                        "entry_price": entry_price,
                        "wallets": list(unique_wallets),
                        "time": datetime.utcnow().isoformat(),
                        "size": size
                    }

                    open_clusters.append(cluster)
                    save_json(OPEN_CLUSTERS_FILE, open_clusters)

                    send_telegram(
                        f"🔥 Cluster Entered\n"
                        f"Market: {market}\n"
                        f"Wallets: {len(unique_wallets)}\n"
                        f"Size: ${round(size,2)}"
                    )

                    recent_trades[market] = []

            time.sleep(5)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)
