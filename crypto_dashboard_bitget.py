import streamlit as st
import pandas as pd
import ccxt
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Crypto Dashboard & Analysis", layout="wide")

# 🔄 Auto-refresh every 5 minutes
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

# Bitget exchange
exchange = ccxt.bitget({"enableRateLimit": True})

st.title("📊 Crypto Dashboard + Buy/Sell Analysis")


# --- Fetch OHLCV (Daily for long history) ---
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


# --- Compute Stats ---
def compute_stats(symbol):
    # Use daily data for long-term highs/lows
    df_daily = fetch_ohlcv(symbol, timeframe="1d", limit=1500)
    if df_daily is None or df_daily.empty:
        return None

    now = df_daily["close"].iloc[-1]

    # Periods in days
    periods_days = {
        "24H": 1,
        "1W": 7,
        "1M": 30,
        "2M": 60,
        "6M": 180,
    }

    stats = {"Current": now}

    for label, days in periods_days.items():
        if len(df_daily) >= days:
            sub = df_daily.tail(days)
            stats[f"A_{label}"] = sub["close"].mean()
            stats[f"H_{label}"] = sub["high"].max()
            stats[f"L_{label}"] = sub["low"].min()
        else:
            stats[f"A_{label}"] = None
            stats[f"H_{label}"] = None
            stats[f"L_{label}"] = None

    # True all-time high & low
    stats["EH"] = df_daily["high"].max()
    stats["EL"] = df_daily["low"].min()

    return stats


# --- Collect Data ---
results = []
for coin in COINS:
    symbol = coin.replace("USDT", "/USDT")
    stats = compute_stats(symbol)
    if stats is not None:
        stats["Symbol"] = coin
        results.append(stats)

if results:
    df = pd.DataFrame(results)

    # --- Analysis Table ---
    analysis = df[
        [
            "Symbol",
            "Current",
            "L_24H",
            "L_1W",
            "L_1M",
            "L_2M",
            "L_6M",
            "EL",
            "H_24H",
            "H_1W",
            "H_1M",
            "H_2M",
            "H_6M",
            "EH",
        ]
    ].copy()

    analysis["Best_Buy_Level"] = analysis[
        ["L_24H", "L_1W", "L_1M", "L_2M", "L_6M", "EL"]
    ].min(axis=1)
    analysis["Best_Sell_Level"] = analysis[
        ["H_24H", "H_1W", "H_1M", "H_2M", "H_6M", "EH"]
    ].max(axis=1)
    analysis["Stop_Loss"] = analysis["Best_Buy_Level"] * 0.95  # 5% below buy

    # % Differences
    analysis["Diff_vs_Buy_%"] = (
        (analysis["Current"] - analysis["Best_Buy_Level"])
        / analysis["Best_Buy_Level"]
    ) * 100
    analysis["Diff_vs_Sell_%"] = (
        (analysis["Current"] - analysis["Best_Sell_Level"])
        / analysis["Best_Sell_Level"]
    ) * 100
    analysis["Potential_Profit_%"] = (
        (analysis["Best_Sell_Level"] - analysis["Best_Buy_Level"])
        / analysis["Best_Buy_Level"]
        * 100
    )

    # --- Smart formatting for prices ---
    def smart_format(val):
        try:
            val = float(val)
            if abs(val) < 1:
                return f"{val:.8f}"
            elif abs(val) < 100:
                return f"{val:.6f}"
            else:
                return f"{val:.2f}"
        except:
            return val

    # --- Styling for table ---
    def color_percent(val):
        if pd.isna(val):
            return ""
        color = "green" if val > 0 else "red"
        return f"color: {color}; font-weight: bold"

    styled_df = analysis.style.format(
        {
            "Current": smart_format,
            "Best_Buy_Level": smart_format,
            "Best_Sell_Level": smart_format,
            "Stop_Loss": smart_format,
            "Diff_vs_Buy_%": "{:.2f}%",
            "Diff_vs_Sell_%": "{:.2f}%",
            "Potential_Profit_%": "{:.2f}%",
        }
    ).applymap(
        color_percent,
        subset=["Diff_vs_Buy_%", "Diff_vs_Sell_%", "Potential_Profit_%"],
    )

    # --- Show Pivot Table ---
    st.subheader("📋 Buy/Sell Analysis Table (with Stop Loss and %)")
    st.dataframe(styled_df, use_container_width=True)

    # --- Coin Selector ---
    coin = st.selectbox("🔍 Select a coin for detailed summary", analysis["Symbol"].unique())

    if coin:
        row = analysis[analysis["Symbol"] == coin].iloc[0]

        # Strategy Summary
        st.success(
            f"""
            **{coin} Strategy**
            - 🛑 Stop Loss: {smart_format(row['Stop_Loss'])}
            - ✅ Suggested Buy: {smart_format(row['Best_Buy_Level'])}
            - 📍 Current: {smart_format(row['Current'])}
            - 🎯 Take Profit: {smart_format(row['Best_Sell_Level'])}

            **Price Differences**
            - Current vs Buy: {row['Diff_vs_Buy_%']:.2f}%
            - Current vs Sell: {row['Diff_vs_Sell_%']:.2f}%
            - Potential Gain (Buy → Sell): {row['Potential_Profit_%']:.2f}%
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
