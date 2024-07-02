import os
import requests
import mplfinance as mpf
import pandas as pd
import numpy as np
import matplotlib.ticker as ticker
from pytz import timezone
from dotenv import load_dotenv

from bitflyer_actions import (
    get_balance,
    get_ltp,
    create_order,
    sell_order,
    buy_order,
    is_valid_order,
)

load_dotenv()

EMA_TESTS = True
EMA_PERIOD = 50

COIN_API_KEY = os.getenv("COIN_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "local_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_DATA = os.path.join(OUTPUT_DIR, "data.csv")
HA_DATA = os.path.join(OUTPUT_DIR, "heikin_ashi.csv")
SMA_DATA = os.path.join(OUTPUT_DIR, "sma_data.csv")
EMA_DATA = os.path.join(OUTPUT_DIR, "ema_data.csv")
EMA_DATA2 = os.path.join(OUTPUT_DIR, "ema_data_before.csv")

JST = timezone("Asia/Tokyo")

ENTRIES_PER_UPDATE = 50
MAX_ENTRIES = 500

CHART_DURATION = 168  # 1 Week (168 hours)

MPF_PLOT = os.path.join(OUTPUT_DIR, "candlestick_plot.png")


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


def calculate_ema(df, period, column="Close"):
    df = df.copy()
    df["EMA"] = df[column].ewm(span=period, adjust=False).mean()
    df["Signal"] = (
        df["EMA"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    )
    return df


def fetch_csv_data(limit):
    print(f"Retrieving {ENTRIES_PER_UPDATE} entries from CryptoCompare")
    data_array = fetch_ohlcv_using_cryptocompare(limit)["Data"]["Data"]
    df = pd.DataFrame(data_array)
    df = df[["time", "close", "high", "low", "open"]]
    df.rename(
        columns={
            "time": "Time",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        },
        inplace=True,
    )
    return df


def update_csv_data(df, output):
    df.to_csv(output, index=False)
    return df


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

    # Keep the original columns and replace open, High, Low, Close
    ha_df["Open"] = ha_df["HA_Open"]
    ha_df["High"] = ha_df["HA_High"]
    ha_df["Low"] = ha_df["HA_Low"]
    ha_df["Close"] = ha_df["HA_Close"]

    # Drop the temporary HA columns
    ha_df.drop(columns=["HA_Open", "HA_High", "HA_Low", "HA_Close"], inplace=True)

    ha_df.to_csv(HA_DATA, index=False)

    return ha_df


def prepare_mpf(df):
    # Convert to datetime and then to JST
    df["Time"] = pd.to_datetime(df["Time"], unit="s")
    df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(JST)

    return df


def mpf_plot(df, range, ema_tests=False, period=EMA_PERIOD, position="HOLDING"):
    # Set the 'time' column as the index
    df.set_index("Time", inplace=True)

    # Create the plot and return the figure and list of axes objects
    fig, axes = mpf.plot(
        df[-range:],
        type="candle",
        style="charles",
        addplot=mpf.make_addplot(df["EMA"][-range:], color="blue"),
        title=f"{period}-HOUR EMA -- {position}",
        ylabel="Price",
        returnfig=True,  # Return the figure and axes objects for further customization
        tight_layout=False,
    )

    # Set the y-axis formatter to avoid scientific notation
    # Assuming the first axis is the one you want to modify
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Save the figure to a file
    if ema_tests:
        fig.savefig(os.path.join(OUTPUT_DIR, f"EMA-{period}"))
    else:
        fig.savefig(MPF_PLOT)


def generate_signal(df):
    if len(df) < 3:
        return 0
    x, y, z = df["Close"].tail(3).values
    if x < y < z:
        return 1
    elif x > y > z:
        return -1
    return 0


def place_order(ema_signal, buy_signal, ltp, bal_jpy, bal_btc):
    order = True
    position = ""
    # if ema_signal == 1 and buy_signal == 1:
    if buy_signal == 1:
        if buy_order(bal_jpy, ltp):
            order = create_order("BTC_JPY", buy_order(bal_jpy, ltp, order=True), "BUY")
        position = "BUY"
    # elif ema_signal == -1:
    #     print("--> EMA signals BEAR market...")
    #     print("--> Selling units to limit losses")
    #     bal_btc = sell_order(bal_btc, ltp, order=True, override=True)
    #     if is_valid_order(bal_btc):
    #         order = create_order("BTC_JPY", bal_btc, "SELL")
    #     else:
    #         print("--> Exiting: Minimum order size is 0.001 BTC")
    #     position = "SELL"
    elif buy_signal == -1:
        # Check if we are making a profit before selling
        if sell_order(bal_btc, ltp):
            bal_btc = sell_order(bal_btc, ltp, order=True)
            order = create_order("BTC_JPY", bal_btc, "SELL")
        position = "SELL"
    elif buy_signal == 0:
        print("Price fluctuating --HOLDING")
        position = "HOLD"
    if order == None:
        # Order was not successful
        print("Order Unsuccessful")
    return position


if __name__ == "__main__":
    print("Starting script...")

    bal_JPY = get_balance("JPY")
    bal_BTC = get_balance("BTC")

    ltp = get_ltp("BTC_JPY")

    print(f"Last trade price: {ltp}")

    get_new_data = True

    if OUTPUT_DIR == "docs":
        get_new_data = True
        EMA_TESTS = False

    if get_new_data == True:
        try:
            df = pd.read_csv(CSV_DATA)
            get_data = fetch_csv_data(ENTRIES_PER_UPDATE)
            new_df_filtered = get_data[~get_data["Time"].isin(df["Time"])]
            df = pd.concat([df, new_df_filtered], ignore_index=True)
        except:
            df = fetch_csv_data(MAX_ENTRIES)

        # Limit the number of entries kept on record
        df = df.tail(MAX_ENTRIES)
        df.to_csv(CSV_DATA, index=False)
    else:
        try:
            df = pd.read_csv(CSV_DATA)
        except:
            print("Error: Could not find CSV data")

    df = calculate_ema(df, period=EMA_PERIOD)

    df = to_heikin_ashi(df)

    df = prepare_mpf(df)

    ema_signal = df.tail(1)["Signal"].iloc[0]
    buy_signal = generate_signal(df)

    print(f"EMA Signal: {ema_signal}")

    print(f"BUY Signal: {buy_signal}")

    # retain chart info for only the last 2 weeks
    df = df.tail(CHART_DURATION)

    df.to_csv(EMA_DATA, index=False)

    position = place_order(
        ema_signal,
        buy_signal,
        get_ltp("BTC_JPY"),
        get_balance("JPY"),
        get_balance("BTC"),
    )

    # plot chart for 2 weeks
    mpf_plot(df, range=CHART_DURATION, position=position)

    if EMA_TESTS:
        for ema_duration in range(50, 250, 50):
            df = pd.read_csv(CSV_DATA)
            df = calculate_ema(df, period=ema_duration)
            df = to_heikin_ashi(df)
            df = prepare_mpf(df)
            ema_signal = df.tail(1)["Signal"].iloc[0]
            buy_signal = generate_signal(df)
            mpf_plot(
                df,
                range=CHART_DURATION,
                ema_tests=EMA_TESTS,
                period=ema_duration,
                position=position,
            )

    print("Script finished.")
