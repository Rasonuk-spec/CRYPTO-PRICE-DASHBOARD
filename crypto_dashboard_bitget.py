import streamlit as st
import pandas as pd
import ccxt
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Crypto Average Price Dashboard", layout="wide")

# Auto-refresh every 5 minutes
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

exchange = ccxt.bitget({"enableRateLimit": True})

st.title("📊 Crypto Dashboard — Average Prices & % Changes")


def fetch_ohlcv(symbol, timeframe="1d", limit=1500):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(
            data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception:
        return None


def compute_stats(symbol):
    df = fetch_ohlcv(symbol, "1d", 1500)
    if df is None or df.empty:
        return None

    now = df["close"].iloc[-1]

    periods = {
        "24H": 1,
        "1W": 7,
        "1M": 30,
        "2M": 60,
        "6M": 180,
    }

    stats = {"Coin": symbol.split("/")[0], "Current": now}

    # Ever averages
    stats["Ever High"] = df["high"].max()
    stats["Ever Low"] = df["low"].min()
    stats["Avg Ever"] = df["close"].mean()

    for label, days in periods.items():
        if len(df) >= days:
            sub = df.tail(days)
            stats[f"High {label}"] = sub["high"].max()
            stats[f"Low {label}"] = sub["low"].min()
            stats[f"Avg {label}"] = sub["close"].mean()
            stats[f"% Change {label}"] = ((sub["high"].max() - sub["low"].min()) / sub["low"].min()) * 100
        else:
            stats[f"High {label}"] = None
            stats[f"Low {label}"] = None
            stats[f"Avg {label}"] = None
            stats[f"% Change {label}"] = None

    return stats


# Collect all data
rows = []
for coin in COINS:
    sym = coin.replace("USDT", "/USDT")
    data = compute_stats(sym)
    if data:
        rows.append(data)

if not rows:
    st.error("⚠️ No data available. Check yo
