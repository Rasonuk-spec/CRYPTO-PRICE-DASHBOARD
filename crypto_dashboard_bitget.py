import streamlit as st
import pandas as pd
import ccxt
import json
import numpy as np
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder

st.set_page_config(page_title="Crypto Dashboard", layout="wide")

# 🔄 Auto-refresh every 5 minutes
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

# Bitget exchange
exchange = ccxt.bitget({"enableRateLimit": True})

st.title("📊 Crypto Dashboard")


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

    # Always include Ever High / Low
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

    # --- % Change calculations ---
    def percent_change(current, ref):
        if ref and ref != 0:
            return round(((current - ref) / ref) * 100, 2)
        return None

    df["%_vs_1W"] = df.apply(
        lambda r: percent_change(r["Current"], r["A_1W"]), axis=1
    )
    df["%_vs_1M"] = df.apply(
        lambda r: percent_change(r["Current"], r["A_1M"]), axis=1
    )

    # --- Format % columns with colored markers ---
    def format_pct(x):
        if x is None or x == "-":
            return "-"
        if x > 0:
            return f"+{x}% ▲🟢"
        elif x < 0:
            return f"{x}% ▼🔴"
        return f"{x}%"

    df["%_vs_1W"] = df["%_vs_1W"].apply(format_pct)
    df["%_vs_1M"] = df["%_vs_1M"].apply(format_pct)

    # --- Reorder columns ---
    df = df[
        [
            "Symbol",
            "Current",
            "A_24H",
            "A_1W",
            "A_1M",
            "H_24H",
            "H_1W",
            "H_1M",
            "L_24H",
            "L_1W",
            "L_1M",
            "EH",
            "EL",
            "%_vs_1W",
            "%_vs_1M",
        ]
    ]

    # --- Sanitize values ---
    df = df.replace([np.inf, -np.inf], None)
    df = df.fillna("-")

    def safe_num(x):
        if isinstance(x, (np.generic,)):
            return x.item()
        if isinstance(x, (int, float)):
            return round(x, 4)
        return x

    df = df.applymap(safe_num)

    # 🔒 Force to string (prevents React errors)
    df = df.astype(str)

    # --- AgGrid Config ---
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_default_column(
        sortable=False,
        filter=False,
        resizable=True,
        suppressMenu=True,
        autoSizeColumns=True,
        wrapHeaderText=True,
        autoHeaderHeight=True,
    )

    gb.configure_column("Symbol", pinned="left")
    gb.configure_column("Current", pinned="left", cellStyle={"fontWeight": "bold"})

    gb.configure_column("EH", cellStyle={"backgroundColor": "#fff7b2"})
    gb.configure_column("EL", cellStyle={"backgroundColor": "#cce5ff"})

    grid_options = gb.build()

    # --- Search Box ---
    search_query = st.text_input("🔍 Search Symbol:", value="")
    grid_options["quickFilterText"] = search_query

    # --- Render AgGrid ---
    st.subheader("📋 Market Stats")
    AgGrid(
        df,
        gridOptions=grid_options,
        theme="balham",
        height=600,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=False,  # safe
        enable_enterprise_modules=False,
        update_mode="NO_UPDATE",
    )

    # CSV Export
    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="crypto_dashboard.csv",
        mime="text/csv",
    )

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
