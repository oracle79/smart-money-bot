import os
import time
import requests
import statistics
from web3 import Web3
from datetime import datetime, timedelta
from collections import defaultdict, deque

# ============================================================
# ENV VARIABLES
# ============================================================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# ============================================================
# WEB3 SETUP
# ============================================================

w3 = Web3(Web3.HTTPProvider(RPC))

if not w3.is_connected():
    raise Exception("Web3 not connected")

print("🧠 Quant Engine Online")
print("Polygon block:", w3.eth.block_number)

# ============================================================
# TELEGRAM
# ============================================================

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        )
    except:
        pass

send("🚀 Institutional Quant Engine Online")

# ============================================================
# CONTRACT
# ============================================================

EXCHANGE = Web3.to_checksum_address(
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
)

FILL_TOPIC = w3.keccak(
    text="Fill(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
).hex()

# ============================================================
# A) TRUE TOKEN SIDE DECODING
# ============================================================

def decode_side_from_price(price):
    # Polymarket YES price ranges 0→1
    # If price is high → buying YES
    # If price is low → buying NO
    return "YES" if price >= 0.5 else "NO"

# ============================================================
# B + C) SMART WALLET ENGINE
# ============================================================

class WalletEngine:

    def __init__(self):
        self.wallet_stats = defaultdict(lambda: {
            "total_volume": 0,
            "total_trades": 0,
            "avg_price": 0,
            "score": 0
        })

    def update(self, wallet, price, size):

        stats = self.wallet_stats[wallet]

        stats["total_volume"] += size
        stats["total_trades"] += 1

        # Running average price
        stats["avg_price"] = (
            (stats["avg_price"] * (stats["total_trades"] - 1) + price)
            / stats["total_trades"]
        )

        self.compute_score(wallet)

    def compute_score(self, wallet):

        stats = self.wallet_stats[wallet]

        # Institutional scoring logic
        volume_factor = min(stats["total_volume"] / 5000, 1)
        activity_factor = min(stats["total_trades"] / 50, 1)

        stats["score"] = round((volume_factor * 0.6 + activity_factor * 0.4), 3)

    def is_smart_money(self, wallet):
        return self.wallet_stats[wallet]["score"] > 0.7

wallet_engine = WalletEngine()

# ============================================================
# MARKET ENGINE
# ============================================================

class MarketEngine:

    def __init__(self):
        self.trades = defaultdict(lambda: deque(maxlen=3000))
        self.metrics = {}

    def update(self, market_id, price, size, side):

        self.trades[market_id].append({
            "price": price,
            "size": size,
            "side": side,
            "time": datetime.utcnow()
        })

        self.compute(market_id)

    def compute(self, market_id):

        now = datetime.utcnow()
        trades = self.trades[market_id]

        window = [
            t for t in trades
            if t["time"] >= now - timedelta(minutes=30)
        ]

        if not window:
            return

        prices = [t["price"] for t in window]
        total_vol = sum(t["size"] for t in window)

        vwap = sum(t["price"] * t["size"] for t in window) / total_vol
        ret = (prices[-1] - prices[0]) / prices[0] if len(prices) > 1 else 0
        vol = statistics.stdev(prices) if len(prices) > 1 else 0

        yes_vol = sum(t["size"] for t in window if t["side"] == "YES")
        no_vol = sum(t["size"] for t in window if t["side"] == "NO")

        imbalance = (yes_vol - no_vol) / total_vol if total_vol else 0

        self.metrics[market_id] = {
            "vwap": vwap,
            "return": ret,
            "vol": vol,
            "imbalance": imbalance
        }

market_engine = MarketEngine()

# ============================================================
# D) RISK + PAPER EXECUTION ENGINE
# ============================================================

class PaperTrader:

    def __init__(self):
        self.capital = 10000
        self.positions = defaultdict(float)

    def evaluate_signal(self, market_id):

        m = market_engine.metrics.get(market_id)
        if not m:
            return

        # Institutional signal logic
        if m["imbalance"] > 0.6 and m["return"] > 0:
            self.buy(market_id, 500)

        elif m["imbalance"] < -0.6 and m["return"] < 0:
            self.sell(market_id, 500)

    def buy(self, market_id, size):

        if self.capital < size:
            return

        self.capital -= size
        self.positions[market_id] += size

        send(f"📈 PAPER BUY\nMarket: {market_id}\nSize: {size}\nCapital: {round(self.capital,2)}")

    def sell(self, market_id, size):

        if self.positions[market_id] < size:
            return

        self.capital += size
        self.positions[market_id] -= size

        send(f"📉 PAPER SELL\nMarket: {market_id}\nSize: {size}\nCapital: {round(self.capital,2)}")

paper = PaperTrader()

# ============================================================
# DECODER
# ============================================================

def decode_fill(log):

    topics = log["topics"]
    data_hex = log["data"].hex()

    chunks = [data_hex[i:i+64] for i in range(0, len(data_hex), 64)]

    try:
        maker_amount = int(chunks[1], 16)
        taker_amount = int(chunks[2], 16)
    except:
        return None

    if maker_amount == 0:
        return None

    price = taker_amount / maker_amount
    size = maker_amount / 1e6

    side = decode_side_from_price(price)

    wallet = "0x" + topics[2].hex()[-40:]
    market_id = topics[1].hex()

    return wallet, market_id, price, size, side

# ============================================================
# MAIN LOOP
# ============================================================

last_block = w3.eth.block_number

while True:

    try:
        current = w3.eth.block_number

        if current > last_block:

            logs = w3.eth.get_logs({
                "fromBlock": last_block + 1,
                "toBlock": current,
                "address": EXCHANGE,
                "topics": [FILL_TOPIC]
            })

            for log in logs:

                decoded = decode_fill(log)
                if not decoded:
                    continue

                wallet, market_id, price, size, side = decoded

                wallet_engine.update(wallet, price, size)
                market_engine.update(market_id, price, size, side)

                if wallet_engine.is_smart_money(wallet):
                    send(f"🐳 Smart Wallet Detected\nWallet: {wallet}\nSize: {round(size,2)}")

                paper.evaluate_signal(market_id)

            last_block = current

        time.sleep(4)

    except Exception as e:
        print("Error:", e)
        time.sleep(4)
