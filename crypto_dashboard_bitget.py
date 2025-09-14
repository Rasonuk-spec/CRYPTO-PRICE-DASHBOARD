import streamlit as st
import pandas as pd
import ccxt
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Crypto Dashboard", layout="wide")

# 🔄 Auto-refresh every 5 minutes (300000 ms)
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

# Bitget exchange
exchange = ccxt.bitget({"enableRateLimit": True})

st.title("📊 Crypto Dashboard (24H candles)")

# --- Fetch OHLCV ---
def fetch_ohlcv(symbol, limit=2000):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=limit)  # 1h candles
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception:
        return None

# --- Compute Stats ---
def compute_stats(df):
    now = df["close"].iloc[-1]
    periods = {
        "24H": 24,
        "1W": 7 * 24,
        "1M": 30 * 24,
        "3M": 90 * 24,
    }
    stats = {"Current": now}
    for label, length in periods.items():
        if len(df) >= length:
            sub = df.tail(length)
            stats[f"Avg_{label}"] = sub["close"].mean()
            stats[f"High_{label}"] = sub["high"].max()
            stats[f"Low_{label}"] = sub["low"].min()
        else:
            stats[f"Avg_{label}"] = None
            stats[f"High_{label}"] = None
            stats[f"Low_{label}"] = None
    return stats

# --- Collect Data ---
results = []
for coin in COINS:
    symbol = coin.replace("USDT", "/USDT")
    df = fetch_ohlcv(symbol)
    if df is not None:
        stats = compute_stats(df)
        stats["Symbol"] = coin
        results.append(stats)

if results:
    df = pd.DataFrame(results)

    # --- % Change calculations ---
    def percent_change(current, ref):
        if ref and ref != 0:
            return round(((current - ref) / ref) * 100, 2)
        return None

    df["%_vs_1W"] = df.apply(lambda r: percent_change(r["Current"], r["Avg_1W"]), axis=1)
    df["%_vs_1M"] = df.apply(lambda r: percent_change(r["Current"], r["Avg_1M"]), axis=1)
    df["%_vs_3M"] = df.apply(lambda r: percent_change(r["Current"], r["Avg_3M"]), axis=1)

    # Reorder columns
    cols = ["Symbol", "Current",
            "Avg_24H", "High_24H", "Low_24H",
            "Avg_1W", "High_1W", "Low_1W", "%_vs_1W",
            "Avg_1M", "High_1M", "Low_1M", "%_vs_1M",
            "Avg_3M", "High_3M", "Low_3M", "%_vs_3M"]
    df = df[cols]

    # Format numbers
    df = df.applymap(lambda x: round(x, 4) if isinstance(x, (int, float)) else x)

    # --- Style Table ---
    def style_table(df):
        def highlight(col):
            if col.name == "Symbol":
                return ["background-color: #2E86C1; color: white; font-weight: bold"] * len(col)
            elif col.name == "Current":
                return ["background-color: #117A65; color: white; font-weight: bold"] * len(col)
            elif "24H" in col.name:
                return ["background-color: #884EA0; color: white"] * len(col)
            elif "1W" in col.name:
                return ["background-color: #CA6F1E; color: white"] * len(col)
            elif "1M" in col.name:
                return ["background-color: #D68910; color: black"] * len(col)
            elif "3M" in col.name:
                return ["background-color: #2874A6; color: white"] * len(col)
            elif "%_" in col.name:
                return ["background-color: #7D3C98; color: white; font-weight: bold"] * len(col)
            else:
                return [""] * len(col)

        return df.style.apply(highlight, axis=0)

    styled_df = style_table(df)

    st.subheader("📋 Market Stats")
    st.dataframe(styled_df, use_container_width=True, height=600)

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
