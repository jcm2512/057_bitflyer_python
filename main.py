import os
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

from cryptocompare import fetch_ohlcv

from chart_actions import append_MCD

load_dotenv()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "local_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOCAL = False
if OUTPUT_DIR == "local_docs":
    LOCAL = True

CSV_DATA = os.path.join(OUTPUT_DIR, "data.csv")
HA_DATA = os.path.join(OUTPUT_DIR, "heikin_ashi.csv")
SMA_DATA = os.path.join(OUTPUT_DIR, "sma_data.csv")
EMA_DATA = os.path.join(OUTPUT_DIR, "ema_data.csv")
EMA_DATA2 = os.path.join(OUTPUT_DIR, "ema_data_before.csv")
DF_SIGNALS = os.path.join(OUTPUT_DIR, "df_signals.csv")

JST = timezone("Asia/Tokyo")

ENTRIES_PER_UPDATE = 50
MAX_ENTRIES = 2000

CHART_DURATION = 168  # 1 Week (168 hours)

MPF_PLOT = os.path.join(OUTPUT_DIR, "candlestick_plot.png")


if __name__ == "__main__":
    print("Starting Main script...")
    df = fetch_ohlcv(CSV_DATA)
    df = append_MCD(df)
    df.to_csv(CSV_DATA)
    print("Script finished.")
