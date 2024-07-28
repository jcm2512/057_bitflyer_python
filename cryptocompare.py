import os
import datetime
import time
import requests
import pandas as pd


from dotenv import load_dotenv


load_dotenv()

COIN_API_KEY = os.getenv("COIN_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")

# Get File Paths
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "local_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOCAL = False
if OUTPUT_DIR == "local_docs":
    LOCAL = True

CSV_DATA = os.path.join(OUTPUT_DIR, "data.csv")
MAX_ENTRIES = 1000


def fetch_ohlcv(csv_data=CSV_DATA, entries_per_update=100):
    now = datetime.datetime.now()
    rounded_down_time = now.replace(minute=0, second=0, microsecond=0)
    previous_hour_timestamp = int(time.mktime(rounded_down_time.timetuple()))

    current_timestamp_exists = False
    if data_exists(csv_data):
        df = pd.read_csv(csv_data)
        if previous_hour_timestamp == int(df.iloc[-1]["Time"]):
            # Data for current timestamp already exists
            current_timestamp_exists = True
    else:
        entries_per_update = 500

    url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=JPY&limit={entries_per_update}&e=Bitflyer"
    headers = {"authorization": CRYPTOCOMPARE_API_KEY}

    if current_timestamp_exists:
        print("Data for current timestamp already exists\n[Aborting Fetch Request]")
        return df
    else:
        response = requests.get(url, headers=headers)

    # Check if the response is successful
    if response.status_code == 200:
        if response.content:
            print(f"Retrieving latest {entries_per_update} entries from CryptoCompare")
            data_array = response.json()["Data"]["Data"]
            new_data = pd.DataFrame(data_array)
            new_data = new_data[["time", "close", "high", "low", "open"]]
            new_data.rename(
                columns={
                    "time": "Time",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                },
                inplace=True,
            )

            if data_exists(csv_data):
                new_data = new_data[~new_data["Time"].isin(df["Time"])]
                df = pd.concat([df, new_data], ignore_index=True)
                df = df.tail(MAX_ENTRIES)
            else:
                df = new_data

            df.to_csv(csv_data, index=False)
            return df
        else:
            print("Response is empty.")
            return None
    else:
        # Handle other HTTP status codes
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None


def data_exists(csv_data):
    try:
        df = pd.read_csv(csv_data)
        if df.shape[0] < 200:
            return False
        return True
    except:
        return False


if __name__ == "__main__":
    print("Starting script...")
    df = fetch_ohlcv()
