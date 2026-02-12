import requests
import time
from datetime import datetime

# ==============================
# CONFIG
# ==============================

SMART_WALLETS = {
    "0x6d3c5bd13984b2de47c3a88ddc455309aab3d294".lower(),
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf".lower(),
    "0x204f72f35326db932158cba6adff0b9a1da95e14".lower()
}

TELEGRAM_TOKEN = "8520159588:AAGD8tjEWwDpStwKHQTx8fvXLvRL-5WS3MI"
TELEGRAM_CHAT_ID = "7154046718"

MIN_TRADE_USD = 1  # $1 threshold for testing

# ==============================
# TELEGRAM FUNCTION
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
# FETCH RECENT TRADES
# ==============================

def fetch_recent_trades():
    url = "https://clob.polymarket.com/trades"
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        print("Trade fetch error:", e)
        return []


# ==============================
# FETCH MARKET INFO
# ==============================

def fetch_market_info(market_id):
    try:
        url = f"https://clob.polymarket.com/markets/{market_id}"
        r = requests.get(url, timeout=10)
        data = r.json()

        event_name = data.get("question", "Unknown Event")
        yes_price = data.get("bestBid", "N/A")
        no_price = data.get("bestAsk", "N/A")

        return event_name, yes_price, no_price
    except Exception as e:
        print("Market fetch error:", e)
        return "Unknown Event", "N/A", "N/A"


# ==============================
# ENGINE LOOP
# ==============================

print("🧠 Smart Wallet API Engine Online")
print(f"Tracking {len(SMART_WALLETS)} wallets")
print("Monitoring Polymarket trades...")

seen_trade_ids = set()

while True:
    try:
        trades = fetch_recent_trades()

        for trade in trades:
            trade_id = trade.get("id")
            if not trade_id:
                continue

            if trade_id in seen_trade_ids:
                continue

            seen_trade_ids.add(trade_id)

            wallet = trade.get("maker", "").lower()
            if wallet not in SMART_WALLETS:
                continue

            size = float(trade.get("size", 0))
            price = float(trade.get("price", 0))
            side = trade.get("side", "").upper()
            market_id = trade.get("market")

            usd_value = size * price

            if usd_value < MIN_TRADE_USD:
                continue

            event_name, yes_price, no_price = fetch_market_info(market_id)

            message = (
                f"🔥 SMART WALLET TRADE DETECTED\n\n"
                f"Wallet: {wallet}\n"
                f"Event: {event_name}\n\n"
                f"Side: {side}\n"
                f"Trade Size: ${usd_value:.2f}\n\n"
                f"Current YES Price: {yes_price}\n"
                f"Current NO Price: {no_price}\n\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            print(message)
            send_telegram(message)

        print("Alive | API Monitoring")
        time.sleep(15)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(10)
