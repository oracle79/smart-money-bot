import os
import time
import requests
import math
from web3 import Web3
from datetime import datetime, timedelta
from collections import defaultdict, deque

# ============================================================
# ENV
# ============================================================

RPC = os.getenv("RPC")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not RPC:
    raise Exception("RPC not set")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Telegram credentials missing")

# ============================================================
# WEB3
# ============================================================

w3 = Web3(Web3.HTTPProvider(RPC))
if not w3.is_connected():
    raise Exception("Web3 not connected")

print("🧠 Smart Cluster Quant Engine v2 Online")
print("Polygon block:", w3.eth.block_number)

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        )
    except:
        pass

send("🚀 Smart Wallet Quant Engine v2 Online")

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
# HELPERS
# ============================================================

def decode_side(price):
    return "YES" if price >= 0.5 else "NO"

# ============================================================
# WALLET ENGINE (Pro Scoring)
# ============================================================

class WalletEngine:

    def __init__(self):
        self.stats = defaultdict(lambda: {
            "volume": 0,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "realized_pnl": 0,
            "returns": [],
            "positions": {},   # market_id -> entry_price
            "score": 0
        })

    def update_trade(self, wallet, market_id, side, price, size):

        s = self.stats[wallet]

        s["volume"] += size
        s["trades"] += 1

        # If wallet already in position, treat this as exit
        if market_id in s["positions"]:
            entry_price = s["positions"][market_id]

            if side == "YES":
                pnl = (price - entry_price) * size
            else:
                pnl = (entry_price - price) * size

            s["realized_pnl"] += pnl
            s["returns"].append(pnl)

            if pnl > 0:
                s["wins"] += 1
            else:
                s["losses"] += 1

            del s["positions"][market_id]

        else:
            # open position
            s["positions"][market_id] = price

        self.compute_score(wallet)

    def compute_score(self, wallet):

        s = self.stats[wallet]

        if s["trades"] < 30:
            s["score"] = 0
            return

        win_rate = s["wins"] / max(1, s["wins"] + s["losses"])
        roi = s["realized_pnl"] / max(1, s["volume"])

        # Sharpe-style metric
        if len(s["returns"]) > 5:
            avg = sum(s["returns"]) / len(s["returns"])
            variance = sum((x - avg) ** 2 for x in s["returns"]) / len(s["returns"])
            std = math.sqrt(variance)
            sharpe = avg / std if std > 0 else 0
        else:
            sharpe = 0

        volume_factor = min(s["volume"] / 20000, 1)

        s["score"] = round(
            (win_rate * 0.3) +
            (roi * 0.3) +
            (sharpe * 0.2) +
            (volume_factor * 0.2),
            4
        )

    def is_smart(self, wallet):
        return self.stats[wallet]["score"] > 0.6

wallet_engine = WalletEngine()

# ============================================================
# CLUSTER ENGINE (Volume Weighted)
# ============================================================

class ClusterEngine:

    def __init__(self):
        self.trades = defaultdict(lambda: deque(maxlen=300))
        self.window = 20
        self.min_wallets = 3
        self.min_volume = 2000

    def add(self, wallet, market_id, side, size):

        if not wallet_engine.is_smart(wallet):
            return

        self.trades[market_id].append({
            "wallet": wallet,
            "side": side,
            "size": size,
            "time": datetime.utcnow()
        })

    def detect(self, market_id):

        now = datetime.utcnow()
        recent = [
            t for t in self.trades[market_id]
            if t["time"] >= now - timedelta(minutes=self.window)
        ]

        if not recent:
            return None

        yes_wallets = set()
        no_wallets = set()
        yes_volume = 0
        no_volume = 0

        for t in recent:
            if t["side"] == "YES":
                yes_wallets.add(t["wallet"])
                yes_volume += t["size"]
            else:
                no_wallets.add(t["wallet"])
                no_volume += t["size"]

        if len(yes_wallets) >= self.min_wallets and yes_volume >= self.min_volume:
            return "YES"

        if len(no_wallets) >= self.min_wallets and no_volume >= self.min_volume:
            return "NO"

        return None

cluster_engine = ClusterEngine()

# ============================================================
# RISK ENGINE
# ============================================================

class RiskEngine:

    def __init__(self):
        self.capital = 1000
        self.daily_start = 1000
        self.max_daily_loss = 0.05
        self.last_reset = datetime.utcnow().date()

    def reset(self):
        today = datetime.utcnow().date()
        if today != self.last_reset:
            self.daily_start = self.capital
            self.last_reset = today

    def allowed(self):
        self.reset()
        loss = (self.daily_start - self.capital) / self.daily_start
        return loss < self.max_daily_loss

risk = RiskEngine()

# ============================================================
# PAPER TRADER
# ============================================================

class PaperTrader:

    def __init__(self):
        self.positions = {}

    def trade(self, market_id, direction):

        if not risk.allowed():
            return

        size = risk.capital * 0.1
        risk.capital -= size

        send(f"""
🔥 SMART CLUSTER SIGNAL
Market: {market_id[:12]}
Direction: {direction}
Position Size: {round(size,2)}
Capital Remaining: {round(risk.capital,2)}
""")

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
    side = decode_side(price)

    wallet = "0x" + topics[2].hex()[-40:]
    market_id = topics[1].hex()

    return wallet, market_id, side, size, price

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

                wallet, market_id, side, size, price = decoded

                wallet_engine.update_trade(wallet, market_id, side, price, size)
                cluster_engine.add(wallet, market_id, side, size)

                direction = cluster_engine.detect(market_id)

                if direction:
                    paper.trade(market_id, direction)

            last_block = current

        time.sleep(4)

    except Exception as e:
        print("Error:", e)
        time.sleep(4)
