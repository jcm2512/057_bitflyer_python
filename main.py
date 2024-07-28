import os
import mplfinance as mpf
import pandas as pd
import numpy as np
import matplotlib.ticker as ticker
from pytz import timezone
from dotenv import load_dotenv

from bitflyer_actions import (
    get_balance,
    get_open_ifd_orders,
    get_current_market_price,
    ifd_order,
    has_funds_for_order,
)

# from cryptocompare import fetch_ohlcv

# from chart_actions import append_MCD, mpf_plot

load_dotenv()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "local_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOCAL = False
if OUTPUT_DIR == "local_docs":
    LOCAL = True

PENDING_ORDERS = os.path.join(OUTPUT_DIR, "pending_orders.csv")
CSV_DATA = os.path.join(OUTPUT_DIR, "data.csv")
HA_DATA = os.path.join(OUTPUT_DIR, "heikin_ashi.csv")
SMA_DATA = os.path.join(OUTPUT_DIR, "sma_data.csv")
EMA_DATA = os.path.join(OUTPUT_DIR, "ema_data.csv")
EMA_DATA2 = os.path.join(OUTPUT_DIR, "ema_data_before.csv")
DF_SIGNALS = os.path.join(OUTPUT_DIR, "df_signals.csv")

JST = timezone("Asia/Tokyo")

ENTRIES_PER_UPDATE = 50
MAX_ENTRIES = 2000

CHART_DURATION = 500  # 7 Days: 168 hours; 3 Days = 72

MIN_PRICE = 9400000
MAX_PRICE = 10600000
PRICE_INTERVAL = 200000

MPF_PLOT = os.path.join(OUTPUT_DIR, "candlestick_plot.png")


def grid_intervals(min=MIN_PRICE, max=MAX_PRICE, interval=PRICE_INTERVAL):
    return [num for num in range(min, max, interval)]


def find_closest_interval(market_price, intervals):
    closest_interval = min(intervals, key=lambda x: abs(x - market_price))
    return closest_interval


def is_open_order(amt, open_orders):
    return amt in open_orders


if __name__ == "__main__":
    print("Starting Main script...")

    grid_interval = PRICE_INTERVAL
    intervals = grid_intervals()
    market_price = get_current_market_price()

    if MIN_PRICE <= market_price <= MAX_PRICE:
        buy_order_amt = find_closest_interval(market_price, intervals)
        ifd_orders = get_open_ifd_orders()

        if not is_open_order(buy_order_amt, ifd_orders):
            if has_funds_for_order(market_price, get_balance("JPY")):
                ifd_order(buy_order_amt, grid_interval)
            else:
                print("INSUFFICIENT FUNDS")
        else:
            print(f"Order:{buy_order_amt} exists \n EXITING...")
    else:
        print("PRICE IS OUT OF RANGE")

    print("DONE")
