import streamlit as st
import pandas as pd
import ccxt
import json

st.set_page_config(page_title="Crypto Dashboard", layout="wide")

# Load coins from JSON
with open("coins.json") as f:
    COINS = json.load(f)

# Use Bitget (no API key required for public data)
exchange = ccxt.bitget({
    "enableRateLimit": True
})

st.title("📊 Crypto Dashboard (15m candles)")

# Fetch OHLCV data from Bitget
def fetch_ohlcv(symbol, limit=1000):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=limit)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df
    except Exception as e:
        st.warning(f"⚠️ No data for {symbol} ({e})")
        return None

# Compute averages, highs, and lows
def compute_stats(df):
    now = df["close"].iloc[-1]
    periods = {
        "24h": 24 * 4,
        "1w": 7 * 24 * 4,
        "1m": 30 * 24 * 4,
        "3m": 90 * 24 * 4,
    }
    stats = {"current": now}
    for label, length in periods.items():
        if len(df) >= length:
            sub = df.tail(length)
            stats[f"avg_{label}"] = sub["close"].mean()
            stats[f"high_{label}"] = sub["high"].max()
            stats[f"low_{label}"] = sub["low"].min()
        else:
            stats[f"avg_{label}"] = None
            stats[f"high_{label}"] = None
            stats[f"low_{label}"] = None
    return stats

results = []
for coin in COINS:
    symbol = coin.replace("USDT", "/USDT")   # Convert ADAUSDT → ADA/USDT
    df = fetch_ohlcv(symbol)
    if df is not None:
        stats = compute_stats(df)
        stats["symbol"] = coin
        results.append(stats)

if results:
    df = pd.DataFrame(results)

    # Add signals
    def signal(row):
        if row["high_3m"] and row["low_3m"]:
            if row["current"] >= 0.95 * row["high_3m"]:
                return "NEAR HIGH"
            elif row["current"] <= 1.05 * row["low_3m"]:
                return "NEAR LOW"
            else:
                return "MID RANGE"
        return "N/A"

    df["signal"] = df.apply(signal, axis=1)

    # Color styling
    def color_signal(val):
        if val == "NEAR HIGH":
            return "background-color: red; color: white"
        elif val == "NEAR LOW":
            return "background-color: green; color: white"
        elif val == "MID RANGE":
            return "background-color: yellow; color: black"
        return ""

    st.dataframe(
        df.style.applymap(color_signal, subset=["signal"]),
        use_container_width=True,
        height=800
    )
else:
    st.error("No data available. Check coins.json or Bitget API.")
