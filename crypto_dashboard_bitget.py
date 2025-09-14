import streamlit as st
import pandas as pd
import ccxt
import json
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Crypto Dashboard", layout="wide")

# 🔄 Auto-refresh every 5 minutes (300000 ms)
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

# Bitget exchange
exchange = ccxt.bitget({"enableRateLimit": True})

st.title("📊 Crypto Dashboard (15m candles)")

# --- Fetch OHLCV ---
def fetch_ohlcv(symbol, limit=3000):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=limit)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception:
        return None

# --- Compute Stats ---
def compute_stats(df):
    now = df["close"].iloc[-1]
    periods = {
        "24H": 24 * 4,
        "1W": 7 * 24 * 4,
        "1M": 30 * 24 * 4,
        "3M": 90 * 24 * 4,
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
        stats["Data"] = df  # keep df for charts
        results.append(stats)

if results:
    df = pd.DataFrame(results)

    # Signal analysis
    def signal(row):
        if row["High_3M"] and row["Low_3M"]:
            if row["Current"] >= 0.95 * row["High_3M"]:
                return "NEAR HIGH"
            elif row["Current"] <= 1.05 * row["Low_3M"]:
                return "NEAR LOW"
            else:
                return "MID RANGE"
        return "N/A"

    df["Signal"] = df.apply(signal, axis=1)

    # Reorder columns (Symbol right after index)
    cols = ["Symbol", "Current", "Avg_24H", "High_24H", "Low_24H",
            "Avg_1W", "High_1W", "Low_1W",
            "Avg_1M", "High_1M", "Low_1M",
            "Avg_3M", "High_3M", "Low_3M",
            "Signal"]
    df = df[cols]

    # Format numbers (remove unnecessary zeros, keep precision)
    df = df.applymap(lambda x: round(x, 4) if isinstance(x, (int, float)) else x)

    # Show dataframe
    st.subheader("📋 Market Stats")
    st.dataframe(df, use_container_width=True, height=600)

    # Charts + analysis for each coin
    st.subheader("📈 3-Month Trend Charts")
    for i, row in df.iterrows():
        coin = row["Symbol"]
        data = results[i]["Data"]

        # Create candlestick chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data["timestamp"],
            open=data["open"], high=data["high"],
            low=data["low"], close=data["close"],
            name=coin
        ))

        fig.update_layout(
            title=f"{coin} - Last 3 Months",
            xaxis_title="Date",
            yaxis_title="Price (USDT)",
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        # Mini analysis
        if row["Signal"] == "NEAR HIGH":
            st.success(f"🚀 {coin} is trading close to its 3M High!")
        elif row["Signal"] == "NEAR LOW":
            st.error(f"📉 {coin} is trading close to its 3M Low!")
        else:
            st.info(f"📊 {coin} is in the mid-range over the last 3 months.")

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
