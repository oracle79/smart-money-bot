from web3 import Web3
import os
import time
import requests

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
POLYGON_RPC = os.getenv("POLYGON_RPC")

# ==============================
# POLYMARKET LEADERBOARD CONFIG
# ==============================
LEADERBOARD_API = "https://data-api.polymarket.com/v1/leaderboard"
TIME_PERIOD = "WEEK"
LIMIT = 500

# ==============================
# CONNECT TO POLYGON
# ==============================
w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

POLYMARKET_EXCHANGE = Web3.to_checksum_address(
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
)

FILL_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8_
