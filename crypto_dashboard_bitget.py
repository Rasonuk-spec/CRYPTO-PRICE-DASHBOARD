import streamlit as st
import pandas as pd
import ccxt
import json
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
            stats[f"Avg_{label}"] = sub["close"].mean()
            stats[f"High_{label}"] = sub["high"].max()
            stats[f"Low_{label}"] = sub["low"].min()
        else:
            stats[f"Avg_{label}"] = None
            stats[f"High_{label}"] = None
            stats[f"Low_{label}"] = None

    # Always include Ever High / Low
    stats["Ever_High"] = df["high"].max()
    stats["Ever_Low"] = df["low"].min()
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
        lambda r: percent_change(r["Current"], r["Avg_1W"]), axis=1
    )
    df["%_vs_1M"] = df.apply(
        lambda r: percent_change(r["Current"], r["Avg_1M"]), axis=1
    )

    # --- Reorder columns ---
    df = df[
        [
            "Symbol",
            "Current",
            "Avg_24H",
            "Avg_1W",
            "Avg_1M",
            "High_24H",
            "High_1W",
            "High_1M",
            "Low_24H",
            "Low_1W",
            "Low_1M",
            "Ever_High",
            "Ever_Low",
            "%_vs_1W",
            "%_vs_1M",
        ]
    ]

    # Round numbers
    df = df.applymap(lambda x: round(x, 4) if isinstance(x, (int, float)) else x)

    # --- AgGrid Config ---
    gb = GridOptionsBuilder.from_dataframe(df)

    # Disable sorting/filter/menu globally
    gb.configure_default_column(
        sortable=False,
        filter=False,
        resizable=True,
        suppressMenu=True,
        autoSizeColumns=True,
        wrapHeaderText=True,
        autoHeaderHeight=True,
    )

    # Symbol and Current pinned left
    gb.configure_column("Symbol", pinned="left")
    gb.configure_column("Current", pinned="left", cellStyle={"fontWeight": "bold"})

    # Conditional formatting for % changes with arrows
    pct_formatter = """function(params) {
        if (params.value == null) return "-";
        if (params.value > 0) return params.value + "% ↑";
        if (params.value < 0) return params.value + "% ↓";
        return params.value + "%";
    }"""

    pct_style = """function(params) {
        if (params.value > 10) {return {color: 'green', fontWeight: 'bold'};}
        if (params.value < -10) {return {color: 'red', fontWeight: 'bold'};}
        if (params.value > 0) {return {color: 'green'};}
        if (params.value < 0) {return {color: 'red'};}
        return {};
    }"""

    gb.configure_column("%_vs_1W", valueFormatter=pct_formatter, cellStyle=pct_style)
    gb.configure_column("%_vs_1M", valueFormatter=pct_formatter, cellStyle=pct_style)

    # Ever High/Low highlighting
    gb.configure_column("Ever_High", cellStyle={"backgroundColor": "#fff7b2"})
    gb.configure_column("Ever_Low", cellStyle={"backgroundColor": "#cce5ff"})

    # Apply config
    grid_options = gb.build()

    # Auto-size all columns on load (fix for scrolling crash)
    grid_options["onFirstDataRendered"] = {
        "function": "params.api.sizeColumnsToFit();"
    }

    # --- Live Search ---
    search_query = st.text_input("🔍 Search Symbol:", value="", key="search")
    grid_options["quickFilterText"] = st.session_state["search"]

    # --- Render AgGrid ---
    st.subheader("📋 Market Stats")
    AgGrid(
        df,
        gridOptions=grid_options,
        theme="balham",
        height=600,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        update_mode="NO_UPDATE",
    )

    # Extra CSV Export Button
    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="crypto_dashboard.csv",
        mime="text/csv",
    )

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
