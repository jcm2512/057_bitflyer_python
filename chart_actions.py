import pandas as pd
import mplfinance as mpf
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

from pytz import timezone


CHART_DURATION = 168


def append_MCD(df, fast, slow, signal):
    df["EMA_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["EMA_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["EMA_fast"] - df["EMA_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Histogram"] = df["MACD"] - df["Signal"]
    return df


def mpf_plot(df, save_file, range=CHART_DURATION):
    # Convert to datetime and then to JST
    df["Time"] = pd.to_datetime(df["Time"], unit="s")
    df["Time"] = df["Time"].dt.tz_localize("UTC").dt.tz_convert(timezone("Asia/Tokyo"))

    # Set the 'time' column as the index
    df.set_index("Time", inplace=True)

    # Determine colors for MACD Histogram bars
    histogram_colors = []
    prev_histogram = (
        df["MACD_Histogram"].iloc[-range - 1]
        if len(df) > range
        else df["MACD_Histogram"].iloc[0]
    )

    for current_histogram in df["MACD_Histogram"][-range:]:
        if current_histogram > 0:
            if current_histogram < prev_histogram:
                histogram_colors.append("lightgreen")
            else:
                histogram_colors.append("green")
        else:
            if current_histogram > prev_histogram:
                histogram_colors.append("lightcoral")  # Light red
            else:
                histogram_colors.append("red")
        prev_histogram = current_histogram

    # Create the plot and return the figure and list of axes objects
    fig, axes = mpf.plot(
        df[-range:],
        type="candle",
        style="charles",
        title=f"BTCJPY MCD",
        ylabel="Price",
        returnfig=True,  # Return the figure and axes objects for further customization
        tight_layout=False,
        xrotation=45,
        addplot=[
            mpf.make_addplot(df["MACD"][-range:], color="purple", width=0.75, panel=1),
            mpf.make_addplot(
                df["Signal"][-range:], color="orange", width=0.75, panel=1
            ),
            mpf.make_addplot(
                df["MACD_Histogram"][-range:],
                type="bar",
                color=histogram_colors,
                panel=1,
                ylabel="",
            ),
        ],
    )

    # Set the y-axis formatter to avoid scientific notation
    # Assuming the first axis is the one you want to modify
    axes[0].xaxis.set_major_locator(mdates.AutoDateLocator())

    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Save the figure to a file
    fig.savefig(save_file)


def generate_mcd_signals(df):
    # Check if dataframe has MCD values
    return
