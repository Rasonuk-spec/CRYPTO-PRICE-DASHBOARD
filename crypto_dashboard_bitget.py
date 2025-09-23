import streamlit as st
import pandas as pd
import ccxt
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Crypto Dashboard + Buy/Sell Analysis", layout="wide")

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

    # --- Base Analysis (Option A) ---
    analysis = df[['Symbol','Current','L_24H','L_1W','L_1M','H_24H','H_1W','H_1M']].copy()

    analysis["Best_Buy_Level"] = analysis[['L_24H','L_1W','L_1M']].min(axis=1)
    analysis["Best_Sell_Level"] = analysis[['H_24H','H_1W','H_1M']].max(axis=1)
    analysis["Stop_Loss"] = analysis["Best_Buy_Level"] * 0.95

    # % Differences
    analysis["Diff_vs_Buy_%"] = ((analysis["Current"] - analysis["Best_Buy_Level"]) / analysis["Best_Buy_Level"]) * 100
    analysis["Diff_vs_Sell_%"] = ((analysis["Current"] - analysis["Best_Sell_Level"]) / analysis["Best_Sell_Level"]) * 100
    analysis["Potential_Profit_%"] = (
        (analysis["Best_Sell_Level"] - analysis["Best_Buy_Level"]) / analysis["Best_Buy_Level"] * 100
    )

    # --- Option B: Advanced Analysis ---
    analysis["Fair_Buy_Range"] = (analysis["L_1W"] + analysis["L_1M"]) / 2
    analysis["Fair_Sell_Range"] = (analysis["H_1W"] + analysis["H_1M"]) / 2
    analysis["Risk_Level"] = analysis["Current"] - analysis["Best_Buy_Level"]
    analysis["Reward_Level"] = analysis["Best_Sell_Level"] - analysis["Current"]
    analysis["Risk_Reward_Ratio"] = analysis["Reward_Level"] / analysis["Risk_Level"]

    # --- Formatting (show up to 8 decimals) ---
    def smart_format(val):
        if pd.isna(val):
            return ""
        if val < 1:
            return f"{val:.8f}"
        elif val < 100:
            return f"{val:.6f}"
        else:
            return f"{val:.2f}"

    styled_df = analysis.style.format(
        {col: smart_format for col in analysis.columns if col not in ["Symbol"]}
    )

    # --- Show Tables ---
    st.subheader("📋 Option A: Clean Buy/Sell Table")
    st.dataframe(styled_df[["Symbol","Current","Best_Buy_Level","Best_Sell_Level","Stop_Loss",
                            "Diff_vs_Buy_%","Diff_vs_Sell_%","Potential_Profit_%"]], use_container_width=True)

    st.subheader("📊 Option B: Advanced Risk/Reward Analysis")
    st.dataframe(styled_df[["Symbol","Current","Best_Buy_Level","Best_Sell_Level","Fair_Buy_Range","Fair_Sell_Range",
                            "Risk_Level","Reward_Level","Risk_Reward_Ratio"]], use_container_width=True)

    # --- Coin Selector ---
    coin = st.selectbox("🔍 Select a coin for detailed summary", analysis["Symbol"].unique())
    if coin:
        row = analysis[analysis["Symbol"] == coin].iloc[0]
        st.success(
            f"""
            **{coin} Strategy**
            - 🛑 Stop Loss: {smart_format(row['Stop_Loss'])}
            - ✅ Suggested Buy: {smart_format(row['Best_Buy_Level'])}
            - 📍 Current: {smart_format(row['Current'])}
            - 🎯 Take Profit: {smart_format(row['Best_Sell_Level'])}

            **Risk/Reward**
            - Risk: {smart_format(row['Risk_Level'])}
            - Reward: {smart_format(row['Reward_Level'])}
            - R/R Ratio: {row['Risk_Reward_Ratio']:.2f}
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
