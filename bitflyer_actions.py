import os
import time
import pandas as pd
import hashlib
import hmac
import requests
import json

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
    url = f"{URL}{path}"

    headers = get_headers(API_KEY, API_SECRET, method, path)
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)

    for balance in response.json():
        if balance["currency_code"] == currency_code:
            return float(balance["amount"])


def get_open_ifd_orders(product_code="BTC_JPY"):
    method = "GET"
    path = "/v1/me/getparentorders"
    params = {"product_code": product_code, "parent_order_state": "ACTIVE"}
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{URL}{path}?{query}"

    headers = get_headers(API_KEY, API_SECRET, method, path + "?" + query)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        orders = response.json()
        ifd_orders = [
            {
                "price": order["price"],
                "parent_order_id": order["parent_order_id"],
                "parent_order_acceptance_id": order["parent_order_acceptance_id"],
            }
            for order in orders
            if order["parent_order_type"] == "IFD"
        ]
        return ifd_orders
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def get_current_market_price(product_code="BTC_JPY"):
    path = "/v1/getticker"
    params = {"product_code": product_code}
    url = f"{URL}{path}"

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get("ltp")  # LTP stands for Last Traded Price
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def has_funds_for_order(market_price, balance, amt=MIN_ORDER, fee=FEE):
    required_jpy = amt * market_price * (1 + fee)
    return balance >= required_jpy


def ifd_order(buy_price, interval, product_code="BTC_JPY", buy_size=MIN_ORDER):
    method = "POST"
    path = "/v1/me/sendparentorder"
    url = f"{URL}{path}"

    body = {
        "order_method": "IFD",
        "time_in_force": "GTC",
        "parameters": [
            {
                "product_code": product_code,
                "condition_type": "LIMIT",
                "side": "BUY",
                "price": buy_price,
                "size": buy_size,
            },
            {
                "product_code": product_code,
                "condition_type": "LIMIT",
                "side": "SELL",
                "price": buy_price + interval,
                "size": buy_size,
            },
        ],
    }

    body_json = json.dumps(body)
    headers = get_headers(API_KEY, API_SECRET, method, path, body_json)

    response = requests.post(url, headers=headers, data=body_json)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def cancel_parent_order(parent_order_acceptance_id, product_code="BTC_JPY"):
    method = "POST"
    path = "/v1/me/cancelparentorder"
    url = f"{URL}{path}"

    body = {
        "product_code": product_code,
        "parent_order_acceptance_id": parent_order_acceptance_id,
    }
    body_json = json.dumps(body)
    headers = get_headers(API_KEY, API_SECRET, method, path, body_json)

    response = requests.post(url, headers=headers, data=body_json)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
