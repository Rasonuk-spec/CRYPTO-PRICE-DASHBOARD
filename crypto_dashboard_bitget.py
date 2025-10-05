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

st.title("📊 Crypto Dashboard — High/Low/Average & % Change")

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
    df_daily = fetch_ohlcv(symbol, timeframe="1d", limit=1500)
    if df_daily is None or df_daily.empty:
        return None

    now = df_daily["close"].iloc[-1]

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
            stats[f"H_{label}"] = sub["high"].max()
            stats[f"L_{label}"] = sub["low"].min()
            stats[f"A_{label}"] = sub["close"].mean()
            stats[f"P_{label}"] = ((stats[f"H_{label}"] - stats[f"L_{label}"]) / stats[f"L_{label}"]) * 100
        else:
            stats[f"H_{label}"] = None
            stats[f"L_{label}"] = None
            stats[f"A_{label}"] = None
            stats[f"P_{label}"] = None

    stats["EH"] = df_daily["high"].max()
    stats["EL"] = df_daily["low"].min()
    stats["A_Ever"] = df_daily["close"].mean()

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
            "H_24H", "A_24H", "L_24H", "P_24H",
            "H_1W", "A_1W", "L_1W", "P_1W",
            "H_1M", "A_1M", "L_1M", "P_1M",
            "H_2M", "A_2M", "L_2M", "P_2M",
            "H_6M", "A_6M", "L_6M", "P_6M",
            "EH", "A_Ever", "EL",
        ]
    ].copy()

    # Sort by 24H percentage change descending
    analysis = analysis.sort_values(by="P_24H", ascending=False)

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

    def format_percent(val):
        try:
            return f"{val:.2f}%"
        except:
            return ""

    styled_df = analysis.style.format(
        {col: smart_format for col in analysis.columns if not col.startswith("P_")}
    ).format(
        {col: format_percent for col in analysis.columns if col.startswith("P_")}
    )

    # --- Show Pivot Table ---
    st.subheader("📋 Multi-Period High / Average / Low + % Change Table")
    st.dataframe(styled_df, use_container_width=True)

    # --- Freeze top row & rightmost column ---
    st.markdown(
        """
        <style>
        [data-testid="stDataFrame"] th {
            position: sticky;
            top: 0;
            background: #0e1117;
            z-index: 2;
        }
        [data-testid="stDataFrame"] td:last-child,
        [data-testid="stDataFrame"] th:last-child {
            position: sticky;
            right: 0;
            background: #0e1117;
            z-index: 1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- CSV Export ---
    st.download_button(
        "📥 Download Analysis CSV",
        analysis.to_csv(index=False).encode("utf-8"),
        file_name="crypto_avg_change_analysis.csv",
        mime="text/csv",
    )

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
