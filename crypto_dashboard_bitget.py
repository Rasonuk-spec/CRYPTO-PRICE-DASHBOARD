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
    st.error("⚠️ No data available. Check your coins.json or Bitget API limits.")
    st.stop()

df = pd.DataFrame(rows)

# Order columns
ordered_cols = [
    "Coin", "Current", "Ever High", "Ever Low", "Avg Ever",
    "High 24H", "Avg 24H", "Low 24H", "% Change 24H",
    "High 1W", "Avg 1W", "Low 1W", "% Change 1W",
    "High 1M", "Avg 1M", "Low 1M", "% Change 1M",
    "High 2M", "Avg 2M", "Low 2M", "% Change 2M",
    "High 6M", "Avg 6M", "Low 6M", "% Change 6M",
]

df = df[ordered_cols]

# Sort by 24H % change (descending)
df = df.sort_values(by="% Change 24H", ascending=False)

# Round numeric columns
for c in df.columns:
    if "% Change" in c:
        df[c] = df[c].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
    elif c not in ["Coin"]:
        df[c] = df[c].apply(lambda x: round(x, 6) if pd.notnull(x) else "")

# Define column group coloring (alternating shades)
col_colors = {
    "24H": "#2a2a2a",
    "1W": "#222233",
    "1M": "#1f332f",
    "2M": "#332222",
    "6M": "#333333",
    "Ever": "#252525",
}

def highlight_cols(col):
    for k, v in col_colors.items():
        if k in col:
            return [f"background-color: {v}; color: white;"] * len(df)
    return [""] * len(df)

styled = df.style.apply(highlight_cols, axis=0)

# Display table
st.dataframe(styled, use_container_width=True)

# Freeze header and coin column
st.markdown("""
<style>
[data-testid="stDataFrame"] th {
  position: sticky;
  top: 0;
  background-color: #111;
  z-index: 1;
}
[data-testid="stDataFrame"] td:first-child,
[data-testid="stDataFrame"] th:first-child {
  position: sticky;
  left: 0;
  background-color: #000;
  z-index: 2;
}
</style>
""", unsafe_allow_html=True)

# Export CSV
st.download_button(
    "📥 Download CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name="crypto_avg_dashboard.csv",
    mime="text/csv"
)
