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

st.title("📊 Crypto Dashboard (24H candles)")


# --- Fetch OHLCV ---
def fetch_ohlcv(symbol, limit=5000):  # ✅ fetch more candles (cover 2M)
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
        "2M": 60 * 24,
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

    df["%_vs_1W"] = df.apply(
        lambda r: percent_change(r["Current"], r["Avg_1W"]), axis=1
    )
    df["%_vs_1M"] = df.apply(
        lambda r: percent_change(r["Current"], r["Avg_1M"]), axis=1
    )
    df["%_vs_2M"] = df.apply(
        lambda r: percent_change(r["Current"], r["Avg_2M"]), axis=1
    )

    # --- Reorder columns ---
    df = df[
        [
            "Symbol",
            "Current",
            "Avg_24H",
            "Avg_1W",
            "Avg_1M",
            "Avg_2M",
            "High_24H",
            "High_1W",
            "High_1M",
            "High_2M",
            "Low_24H",
            "Low_1W",
            "Low_1M",
            "Low_2M",
            "%_vs_1W",
            "%_vs_1M",
            "%_vs_2M",
        ]
    ]

    # Round numbers
    df = df.applymap(lambda x: round(x, 4) if isinstance(x, (int, float)) else x)

    # --- AgGrid Config (NO sorting, NO filter, Auto-fit) ---
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        sortable=False,  # ❌ no sorting
        filter=False,    # ❌ no filtering
        resizable=True,
        autoSizeColumns=True,
        wrapText=True,
    )
    gb.configure_column("Symbol", pinned="left")
    gb.configure_column("Current", pinned="left")

    # Only export + search enabled
    gb.configure_grid_options(
        domLayout="normal",
        enableRangeSelection=False,
        suppressRowClickSelection=True,
        quickFilter=True,
    )
    grid_options = gb.build()

    # ✅ remove flex so columns don’t stretch
    if "flex" in grid_options["defaultColDef"]:
        del grid_options["defaultColDef"]["flex"]

    grid_options["defaultColDef"]["autoSizeAllColumns"] = True
    grid_options["enableExport"] = True

    # --- Search box ---
    search_query = st.text_input("🔍 Search Symbol:", "")
    grid_options["quickFilterText"] = search_query

    # --- Render AgGrid ---
    st.subheader("📋 Market Stats (Auto-fit, Exportable, Searchable)")
    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,  # ✅ shrink to fit content
        theme="balham",
        height=600,
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
