import os
import time
import pandas as pd
import hashlib
import hmac
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "local_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

URL = "https://api.bitflyer.com"

MIN_ORDER = 0.001
FEE = 0.001

PREV_BUY = os.path.join(OUTPUT_DIR, "prev_buy.csv")


def get_headers(api_key, api_secret, method, path, body=""):
    TIMESTAMP = str(int(time.time()))

    # Create the message to be signed
    message = str(TIMESTAMP) + method + path + body

    # Generate the HMAC-SHA256 signature and get it as a hexadecimal string
    signature = hmac.new(
        bytes(api_secret.encode("utf-8")),
        bytes(message.encode("utf-8")),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "ACCESS-KEY": api_key,
        "ACCESS-TIMESTAMP": TIMESTAMP,
        "ACCESS-SIGN": signature,
        "Content-Type": "application/json",
    }
    return headers


def get_balance(currency_code):
    method = "GET"
    path = "/v1/me/getbalance"
    url = URL + path

    headers = get_headers(API_KEY, API_SECRET, method, path)
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)

    for balance in response.json():
        if balance["currency_code"] == currency_code:
            return float(balance["amount"])


def is_valid_order(order, min_order=MIN_ORDER):
    # Checks to see if order is more than the minimum order
    if order > min_order:
        return True
    return False


def get_ltp(currency_pair="BTC_JPY"):
    path = "/v1/ticker"
    params = {"product_code": currency_pair}
    url = URL + path

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        ltp = data["ltp"]
        return float(ltp)  # 'ltp' stands for Last Traded Price
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def sell_order(bal_btc, ltp, fee=FEE, order=False, override=False):
    # Simulates a SELL order and returns a boolean
    # Resets previous BUY order, if set to True
    # If override set to True, will perform sell without checks
    if order:
        print("Generating SELL order...")
    else:
        print("Simulating SELL order...")
    try:
        df = pd.read_csv(PREV_BUY)
        prev_buy = int(df["BUY"].values[0])
    except:
        print("Could not locate CSV for Previous BUY")
        print("Exiting Trade...")
        return False
    sub_total = int(bal_btc * ltp)
    total = int(sub_total - (sub_total * fee))

    # Round down the BTC order, to reduce the purchased units of BTC
    # There may be slight price fluctuations at the time of purchase
    # Which may result in not having enough funds available
    round_down = bal_btc * 0.995

    # Convert to 8 decimal places
    btc_total = float(f"{round_down:.8f}")

    if override:
        print("Stop Loss Trade")
        print("----------------")
        print(f"Previous BUY: ¥{prev_buy:,}")
        print(f"Total Sale Amount: ¥{total:,}")
        print(f"Loss: -¥{prev_buy - total:,}")
        # Reset Previous Buy Order to zero
        df.at[0, "BUY"] = 0
        df.to_csv(PREV_BUY, index=False)
        return btc_total

    if total < prev_buy:
        print(f"Previous BUY: ¥{prev_buy:,}")
        print("--> Exiting Trade: Price Too Low")
        return False

    if order:
        print("Successful Trade")
        print("----------------")
        print(f"Previous BUY: ¥{prev_buy:,}")
        print(f"Total Sale Amount: ¥{total:,}")
        # Reset Previous Buy Order to zero
        df.at[0, "BUY"] = 0
        df.to_csv(PREV_BUY, index=False)

        return btc_total
    return True


def simulate_buy(bal_jpy, ltp, fee=FEE):

    if is_valid_order(ltp, bal_jpy, fee):
        try:
            df = pd.read_csv(PREV_BUY)
            prev_buy = float(df["BUY"].values[0])
        except:
            print("Previous BUY not found")
            prev_buy = 0
        print(f"Funds Available: {float(bal_jpy)}")
        total_purchase = round(float(bal_jpy) / (float(ltp) * (1 + fee)), 6)
        print(f"Last Trade Price: {int(ltp)}")
        print(f"Total Purchase Amount: {total_purchase} units")
        prev_buy = prev_buy + int((total_purchase * float(ltp)) * (1 + fee))
        df = pd.DataFrame({"BUY": [prev_buy]})
        df.to_csv(PREV_BUY, index=False)
        return total_purchase
    else:
        print("Insufficient Funds")


def buy_order(bal_jpy, ltp, fee=FEE, order=False, testing=False):
    # Simulates a BUY order and returns a boolean
    # If order is set to True, will return purchase amount

    if order:
        print("Generating BUY order...")
    else:
        print("Simulating BUY order...")
    btc_order = float(bal_jpy) / (ltp * (1 + fee))
    current_buy = int((float(btc_order) * float(ltp)) * (1 + fee))

    if btc_order > MIN_ORDER:
        try:
            df = pd.read_csv(PREV_BUY)
            prev_buy = float(df["BUY"].values[0])
        except:
            print("Previous BUY not found")
            print("Assuming this is your first BUY order")
            print("--> Resetting Prev BUY to 0")
            prev_buy = 0
        # Round down the BTC order, to reduce the purchased units of BTC
        # There may be slight price fluctuations at the time of purchase
        # Which may result in not having enough funds available
        btc_order_rounded = int(btc_order * 100000) / 100000
        new_buy = prev_buy + current_buy

        if not order or testing:
            print(f"Funds Available: ¥{int(bal_jpy):,}")
            print(f"Last Trade Price: ¥{int(ltp):,}")
            print(f"Total Purchase Amount: {btc_order_rounded } BTC")
            print(f"BUY order: ¥{current_buy:,}")

        if order and not testing:
            df = pd.DataFrame({"BUY": [new_buy]})
            df.to_csv(PREV_BUY, index=False)
        else:
            print("BUY Order Successful")
            return True
        return btc_order_rounded
    else:
        print("--> Exiting Trade: Insufficient Funds")
        return False


def create_order(product_code, size, side):
    method = "POST"
    path = "/v1/me/sendchildorder"
    url = URL + path

    body = {
        "product_code": product_code,
        "child_order_type": "MARKET",
        "side": side,
        "size": size,
    }
    body_json = json.dumps(body)

    headers = get_headers(API_KEY, API_SECRET, method, path, body_json)
    response = requests.post(url, headers=headers, data=body_json)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

    return response.json()


if __name__ == "__main__":
    ltp = get_ltp("BTC_JPY")
    bal_JPY = get_balance("JPY")
    bal_BTC = get_balance("BTC")
    # simulate_sell(bal=get_balance("BTC"), ltp=get_ltp("BTC_JPY"))
    # size = simulate_buy(bal_JPY, ltp)
    # simulate_sell(bal_BTC, ltp)
    # simulate_buy(16130.0, 10216890)
    # print(size)

    # market_sell("ETH_JPY", round(float(get_balance("ETH")), 3))
    # create_order("BTC_JPY", simulate_buy(bal_JPY, ltp), "BUY")
    print(buy_order(15000, 10800000))
