import os
import time
import hashlib
import hmac
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

URL = "https://api.bitflyer.com"

MIN_ORDER = 0.001


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


def is_valid_order(close, bal):
    fee = 1.001
    is_enough = float(bal) / (close * fee)
    if is_enough > MIN_ORDER:
        return True
    return False


def get_btc_jpy_price():
    path = "/v1/ticker"
    params = {"product_code": "BTC_JPY"}
    url = URL + path

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data["ltp"]  # 'ltp' stands for Last Traded Price
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
