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
import matplotlib.ticker as ticker
from pytz import timezone
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
COIN_API_KEY = os.getenv("COIN_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")

URL = "https://api.bitflyer.com"

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "local_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_DATA = os.path.join(OUTPUT_DIR, "data.csv")
HA_DATA = os.path.join(OUTPUT_DIR, "heikin_ashi.csv")
SMA_DATA = os.path.join(OUTPUT_DIR, "sma_data.csv")
EMA_DATA = os.path.join(OUTPUT_DIR, "ema_data.csv")
EMA_DATA2 = os.path.join(OUTPUT_DIR, "ema_data_before.csv")


MPF_PLOT = os.path.join(OUTPUT_DIR, "candlestick_plot.png")

JST = timezone("Asia/Tokyo")

CHART_SPAN = 500
PERIOD = 200

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


def fetch_ohlcv_using_cryptocompare(limit=100):
    url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=JPY&limit={limit}&e=Bitflyer"
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


def calculate_ema(df, period=PERIOD, column="close"):
    df = df.copy()
    df["ema"] = df[column].ewm(span=period, adjust=False).mean()
    df["signal"] = (
        df["ema"]
        .diff()
        .apply(lambda x: "UP" if x > 0 else ("DOWN" if x < 0 else "FLAT"))
    )
    return df


def fetch_csv_data(limit=100):
    data_array = fetch_ohlcv_using_cryptocompare(limit)["Data"]["Data"]
    df = pd.DataFrame(data_array)
    df = df[["time", "close", "high", "low", "open"]]
    return df


def update_csv_data(df, output):
    df.to_csv(output, index=False)
    return df


def to_heikin_ashi(df):

    ha_df = df.copy()

    # Calculate Heikin-Ashi values
    ha_df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_df["HA_Open"] = np.nan
    ha_df.loc[ha_df.index[0], "HA_Open"] = df.loc[ha_df.index[0], "open"]
    for i in range(1, len(ha_df)):
        ha_df.loc[ha_df.index[i], "HA_Open"] = (
            ha_df.loc[ha_df.index[i - 1], "HA_Open"]
            + ha_df.loc[ha_df.index[i - 1], "HA_Close"]
        ) / 2

    ha_df["HA_High"] = ha_df[["high", "HA_Open", "HA_Close"]].max(axis=1)
    ha_df["HA_Low"] = ha_df[["low", "HA_Open", "HA_Close"]].min(axis=1)

    # Keep the original columns and replace open, high, low, close
    ha_df["open"] = ha_df["HA_Open"]
    ha_df["high"] = ha_df["HA_High"]
    ha_df["low"] = ha_df["HA_Low"]
    ha_df["close"] = ha_df["HA_Close"]

    # Drop the temporary HA columns
    ha_df.drop(columns=["HA_Open", "HA_High", "HA_Low", "HA_Close"], inplace=True)

    ha_df.to_csv(HA_DATA, index=False)

    return ha_df


def prepare_mpf(df):
    # Convert to datetime and then to JST
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df["time"] = df["time"].dt.tz_localize("UTC").dt.tz_convert(JST)

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

    return df


def mpf_plot(df, range=200):
    print("Generating CandleStick plot...")

    # Set the 'time' column as the index
    df.set_index("time", inplace=True)

    # Create the plot and return the figure and list of axes objects
    fig, axes = mpf.plot(
        df[-range:],
        type="candle",
        style="charles",
        addplot=mpf.make_addplot(df["ema"][-range:], color="blue"),
        title="Candlestick Chart",
        ylabel="Price",
        returnfig=True,  # Return the figure and axes objects for further customization
        tight_layout=False,
    )

    # Set the y-axis formatter to avoid scientific notation
    # Assuming the first axis is the one you want to modify
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Save the figure to a file
    fig.savefig(MPF_PLOT)
    print(f"CandleStick plot saved as {MPF_PLOT}")


if __name__ == "__main__":
    print("Starting script...")
    df = pd.read_csv(CSV_DATA)
    get_data = fetch_csv_data(50)
    new_df_filtered = get_data[~get_data["time"].isin(df["time"])]
    df = pd.concat([df, new_df_filtered], ignore_index=True)

    # keep only the last 500 entries
    df = df.tail(500)
    df.to_csv(CSV_DATA, index=False)

    df = calculate_ema(df)

    df = to_heikin_ashi(df)

    df = prepare_mpf(df)

    # retain chart info for only the last 2 weeks
    df = df.tail(336)

    df.to_csv(EMA_DATA, index=False)

    # plot chart for 2 weeks
    mpf_plot(df, range=336)

    print("Script finished.")
