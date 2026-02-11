from web3 import Web3
import os

POLYGON_RPC = os.getenv("POLYGON_RPC")

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

def check_connection():
    if w3.is_connected():
        print("Connected to Polygon")
    else:
        print("Connection failed")

if __name__ == "__main__":
    check_connection()
