import os
import time
import pandas as pd
import hashlib
import hmac
import requests
import json

from settings import MIN_ORDER, MIN_BUY_ORDER, FEE, PRODUCT_CODE

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

URL = "https://api.bitflyer.com"


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


def get_parent_orders():
    method = "GET"
    path = "/v1/me/getparentorders"
    params = {
        "product_code": PRODUCT_CODE,
        "parent_order_state": "ACTIVE",
    }
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{URL}{path}?{query}"

    headers = get_headers(API_KEY, API_SECRET, method, path + "?" + query)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        orders = response.json()
        ifd_orders = [order for order in orders if order["parent_order_type"] == "IFD"]
        return ifd_orders
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def get_parent_order(parent_order_acceptance_id):
    method = "GET"
    path = "/v1/me/getparentorder"
    params = {
        "product_code": PRODUCT_CODE,
        "parent_order_acceptance_id": parent_order_acceptance_id,
    }
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{URL}{path}?{query}"

    headers = get_headers(API_KEY, API_SECRET, method, path + "?" + query)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        orders = response.json()
        return orders
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def get_open_limit_orders(side):
    method = "GET"
    path = "/v1/me/getchildorders"
    params = {"product_code": PRODUCT_CODE, "child_order_state": "ACTIVE"}
    query = "&".join(f"{key}={value}" for key, value in params.items())
    url = f"{URL}{path}?{query}"

    headers = get_headers(API_KEY, API_SECRET, method, path + "?" + query)
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        orders = response.json()
        limit_orders = [
            order
            for order in orders
            if order["child_order_type"] == "LIMIT" and order["side"] == side
        ]
        return limit_orders
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def get_current_market_price():
    path = "/v1/getticker"
    params = {"product_code": PRODUCT_CODE}
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


def ifd_order(
    buy_price,
    interval,
    product_code=PRODUCT_CODE,
    buy_size=MIN_BUY_ORDER,
    sell_size=MIN_ORDER,
):
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
                "size": sell_size,
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


def cancel_parent_order(parent_order_acceptance_id):
    method = "POST"
    path = "/v1/me/cancelparentorder"
    url = f"{URL}{path}"

    body = {
        "product_code": PRODUCT_CODE,
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
