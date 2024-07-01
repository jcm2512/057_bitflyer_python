import os
import time
import hashlib
import hmac
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

URL = "https://api.bitflyer.com"

MIN_ORDER = 0.001
FEE = 0.001


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
            return format(balance["amount"], ".8f")


def is_valid_order(close, bal, fee=FEE):
    is_enough = float(bal) / (close * fee)
    if is_enough > MIN_ORDER:
        return True
    return False


def get_ltp(currency_pair="BTC_JPY"):
    path = "/v1/ticker"
    params = {"product_code": currency_pair}
    url = URL + path

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data["ltp"]  # 'ltp' stands for Last Traded Price
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def simulate_sell(bal, ltp, fee=FEE):
    print(f"Balance: {float(bal)}")
    rounded_bal = round(float(bal), 3)
    sub_total = int(rounded_bal * float(ltp))
    total = int(sub_total - (sub_total * fee))

    print(f"Rounded Balance: {float(rounded_bal)}")
    print(f"Last Trade Price: {int(ltp)}")
    print(f"Total Sale Amount: {total} YEN")


def market_sell(product_code, size):
    method = "POST"
    path = "/v1/me/sendchildorder"
    url = URL + path

    body = {
        "product_code": product_code,
        "child_order_type": "MARKET",
        "side": "SELL",
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
    # simulate_sell(bal=get_balance("ETH"), ltp=get_ltp("ETH_JPY"))
    market_sell("ETH_JPY", round(float(get_balance("ETH")), 3))
