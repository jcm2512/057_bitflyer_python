import os
import time
import hashlib
import hmac
import requests
import matplotlib
import mplfinance as mpf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
COIN_API_KEY = os.getenv("COIN_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")

URL = "https://api.bitflyer.com"

CSV_DATA = "data.csv"

matplotlib.use("Agg")


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


def get_executions():
    method = "GET"
    path = "/v1/me/getexecutions"
    url = URL + path

    headers = get_headers(API_KEY, API_SECRET, method, path)
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
    return response.json()


def get_OHLCV():
    url = "https://rest.coinapi.io/v1/ohlcv/exchanges/BITFLYER_SPOT_BTC_JPY/history?period_id=1MTH&time_start=2023-03-01T00:00:00"

    payload = {}
    headers = {"Accept": "text/plain", "X-CoinAPI-Key": COIN_API_KEY}

    response = requests.request("GET", url, headers=headers, data=payload)
    return response.json()


def fetch_ohlcv():
    url = "https://rest.coinapi.io/v1/ohlcv/BITFLYER_SPOT_ETH_BTC/latest?period_id=1DAY"
    headers = {"X-CoinAPI-Key": COIN_API_KEY}  # Replace with your API key

    response = requests.get(url, headers=headers)

    # Check if the response is successful
    if response.status_code == 200:
        if response.content:
            return response.json()
        else:
            print("Response is empty.")
            return None
    else:
        # Handle other HTTP status codes
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None


def fetch_ohlcv_using_cryptocompare():
    url = "https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=JPY&limit=100&e=Bitflyer"
    headers = {"authorization": CRYPTOCOMPARE_API_KEY}

    response = requests.get(url, headers=headers)

    # Check if the response is successful
    if response.status_code == 200:
        if response.content:
            return response.json()
        else:
            print("Response is empty.")
            return None
    else:
        # Handle other HTTP status codes
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None


def update_csv_data():
    data_array = fetch_ohlcv_using_cryptocompare()["Data"]["Data"]
    df = pd.DataFrame(data_array)

    df.to_csv(CSV_DATA, index=False)


def to_heikin_ashi(df):
    ha_df = df.copy()

    # Calculate Heikin-Ashi values
    ha_df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_df["HA_Open"] = np.nan
    ha_df.loc[ha_df.index[0], "HA_Open"] = df.loc[ha_df.index[0], "Open"]
    for i in range(1, len(ha_df)):
        ha_df.loc[ha_df.index[i], "HA_Open"] = (
            ha_df.loc[ha_df.index[i - 1], "HA_Open"]
            + ha_df.loc[ha_df.index[i - 1], "HA_Close"]
        ) / 2

    ha_df["HA_High"] = ha_df[["High", "HA_Open", "HA_Close"]].max(axis=1)
    ha_df["HA_Low"] = ha_df[["Low", "HA_Open", "HA_Close"]].min(axis=1)

    ha_df = ha_df[["HA_Open", "HA_High", "HA_Low", "HA_Close"]]

    ha_df.rename(
        columns={
            "HA_Open": "Open",
            "HA_High": "High",
            "HA_Low": "Low",
            "HA_Close": "Close",
        },
        inplace=True,
    )

    return ha_df


def simple_plot():

    df = pd.read_csv(CSV_DATA)

    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Plot the data
    plt.figure(figsize=(10, 6))

    # Plot the 'close', 'high', and 'low' prices over time
    plt.plot(df["time"], df["close"], label="Close Price")
    plt.plot(df["time"], df["high"], label="High Price", linestyle="--")
    plt.plot(df["time"], df["low"], label="Low Price", linestyle=":")

    # Adding titles and labels
    plt.title("Prices Over Time")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()

    plt.xticks(rotation=45)
    plt.ticklabel_format(style="plain", axis="y")

    plot_file_name = "plot.png"
    plt.savefig(plot_file_name)


def mpf_plot():
    df = pd.read_csv(CSV_DATA)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Set the 'time' column as the index
    df.set_index("time", inplace=True)

    # Rename columns to match mplfinance requirements
    df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        },
        inplace=True,
    )

    ha_df = to_heikin_ashi(df)
    # Save the plot to a file
    mpf.plot(
        ha_df,
        type="candle",
        style="charles",
        title="Candlestick Chart",
        ylabel="Price",
        savefig="candlestick_plot.png",
    )


if __name__ == "__main__":
    mpf_plot()
    print("Hello World")
