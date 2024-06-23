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

JST = timezone("Asia/Tokyo")

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


def convert_to_jst(df, time_column):
    # Convert to datetime and then to JST
    df[time_column] = pd.to_datetime(df[time_column], unit="s")
    df[time_column] = df[time_column].dt.tz_localize("UTC").dt.tz_convert(JST)
    return df


def simple_plot():
    print("Generating simple plot...")

    df = pd.read_csv(CSV_DATA)

    df = convert_to_jst(df, "time")

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

    plot_file_name = os.path.join(OUTPUT_DIR, "plot.png")
    plt.savefig(plot_file_name)
    print(f"Simple plot saved as {plot_file_name}")


def mpf_plot():
    print("Generating CandleStick plot...")

    df = pd.read_csv(CSV_DATA)
    df = convert_to_jst(df, "time")

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
    plot_file_name = os.path.join(OUTPUT_DIR, "candlestick_plot.png")

    # Create the plot and return the figure and list of axes objects
    fig, axes = mpf.plot(
        ha_df,
        type="candle",
        style="charles",
        title="Candlestick Chart",
        ylabel="Price",
        returnfig=True,  # Return the figure and axes objects for further customization
        tight_layout=False,
    )

    # Set the y-axis formatter to avoid scientific notation
    # Assuming the first axis is the one you want to modify
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Save the figure to a file
    fig.savefig(plot_file_name)
    print(f"CandleStick plot saved as {plot_file_name}")


if __name__ == "__main__":
    print("Starting script...")
    update_csv_data()
    simple_plot()
    mpf_plot()
    print("Script finished.")
