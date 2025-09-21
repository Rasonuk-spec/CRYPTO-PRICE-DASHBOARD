import streamlit as st
import pandas as pd
import ccxt
import json
import numpy as np
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

st.set_page_config(page_title="Crypto Dashboard & Analysis", layout="wide")

# 🔄 Auto-refresh every 5 minutes
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

# Bitget exchange
exchange = ccxt.bitget({"enableRateLimit": True})

st.title("📊 Crypto Dashboard + Buy/Sell Analysis")

# --- Fetch OHLCV ---
def fetch_ohlcv(symbol, limit=2000):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=limit)
        df = pd.DataFrame(
            data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
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
    }
    stats = {"Current": now}
    for label, length in periods.items():
        if len(df) >= length:
            sub = df.tail(length)
            stats[f"A_{label}"] = sub["close"].mean()
            stats[f"H_{label}"] = sub["high"].max()
            stats[f"L_{label}"] = sub["low"].min()
        else:
            stats[f"A_{label}"] = None
            stats[f"H_{label}"] = None
            stats[f"L_{label}"] = None

    stats["EH"] = df["high"].max()
    stats["EL"] = df["low"].min()
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

    # --- Analysis Table ---
    analysis = df[['Symbol','Current','L_24H','L_1W','L_1M','EL','H_24H','H_1W','H_1M','EH']].copy()

    analysis["Best_Buy_Level"] = analysis[['L_24H','L_1W','L_1M','EL']].min(axis=1)
    analysis["Best_Sell_Level"] = analysis[['H_24H','H_1W','H_1M','EH']].max(axis=1)
    analysis["Stop_Loss"] = analysis["Best_Buy_Level"] * 0.95   # 5% below buy
    analysis["Potential_Profit_%"] = (
        (analysis["Best_Sell_Level"] - analysis["Best_Buy_Level"]) / analysis["Best_Buy_Level"] * 100
    )

    # --- Show Pivot Table ---
    st.subheader("📋 Buy/Sell Analysis Table (with Stop Loss)")
    st.dataframe(analysis, use_container_width=True)

    # --- Coin Selector ---
    coin = st.selectbox("🔍 Select a coin for detailed chart", analysis["Symbol"].unique())

    if coin:
        row = analysis[analysis["Symbol"] == coin].iloc[0]

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Stop Loss", "Best Buy", "Current Price", "Best Sell"],
            y=[row["Stop_Loss"], row["Best_Buy_Level"], row["Current"], row["Best_Sell_Level"]],
            marker_color=["orange", "green", "blue", "red"]
        ))
        fig.update_layout(
            title=f"📈 {coin} Buy/Sell Strategy with SL",
            yaxis_title="Price (USDT)",
            xaxis_title="Levels"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Strategy Summary
        st.success(
            f"""
            **{coin} Strategy**
            - 🛑 Stop Loss: {row['Stop_Loss']:.2f}
            - ✅ Suggested Buy: {row['Best_Buy_Level']:.2f}
            - 📍 Current: {row['Current']:.2f}
            - 🎯 Take Profit: {row['Best_Sell_Level']:.2f}
            - 📊 Potential Gain: {round(row['Potential_Profit_%'], 2)}%
            """
        )

    # --- CSV Export ---
    st.download_button(
        "📥 Download Analysis CSV",
        analysis.to_csv(index=False).encode("utf-8"),
        file_name="crypto_analysis.csv",
        mime="text/csv",
    )

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
