import streamlit as st
import pandas as pd
import ccxt
import json
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
def fetch_ohlcv(symbol, limit=2000):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=limit)
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

    df["%_vs_1W"] = df.apply(lambda r: percent_change(r["Current"], r["Avg_1W"]), axis=1)
    df["%_vs_1M"] = df.apply(lambda r: percent_change(r["Current"], r["Avg_1M"]), axis=1)
    df["%_vs_2M"] = df.apply(lambda r: percent_change(r["Current"], r["Avg_2M"]), axis=1)

    # --- Reorder columns ---
    df = df[[
        "Symbol", "Current",
        "Avg_24H", "Avg_1W", "Avg_1M", "Avg_2M",
        "High_24H", "High_1W", "High_1M", "High_2M",
        "Low_24H", "Low_1W", "Low_1M", "Low_2M",
        "%_vs_1W", "%_vs_1M", "%_vs_2M"
    ]]

    # Round numbers
    df = df.applymap(lambda x: round(x, 4) if isinstance(x, (int, float)) else x)

    # --- AgGrid Config ---
    gb = GridOptionsBuilder.from_dataframe(df)

    # Enable sorting/filtering/resizing
    gb.configure_default_column(sortable=True, filter=True, resizable=True)

    # Pin Symbol + Current
    gb.configure_column("Symbol", pinned="left")
    gb.configure_column("Current", pinned="left")

    # Conditional formatting for % Change
    def cell_style(params):
        try:
            val = float(params.value)
            if val > 0:
                return {"color": "green", "fontWeight": "bold"}
            elif val < 0:
                return {"color": "red", "fontWeight": "bold"}
        except:
            return {"color": "black"}
        return {"color": "black"}

    for col in ["%_vs_1W", "%_vs_1M", "%_vs_2M"]:
        gb.configure_column(col, cellStyle=cell_style)

    # --- Column Grouping (Multi-level headers) ---
    gb.configure_column("Avg_24H", header_name="24H", parent="Avg Values")
    gb.configure_column("Avg_1W", header_name="1W", parent="Avg Values")
    gb.configure_column("Avg_1M", header_name="1M", parent="Avg Values")
    gb.configure_column("Avg_2M", header_name="2M", parent="Avg Values")

    gb.configure_column("High_24H", header_name="24H", parent="High Values")
    gb.configure_column("High_1W", header_name="1W", parent="High Values")
    gb.configure_column("High_1M", header_name="1M", parent="High Values")
    gb.configure_column("High_2M", header_name="2M", parent="High Values")

    gb.configure_column("Low_24H", header_name="24H", parent="Low Values")
    gb.configure_column("Low_1W", header_name="1W", parent="Low Values")
    gb.configure_column("Low_1M", header_name="1M", parent="Low Values")
    gb.configure_column("Low_2M", header_name="2M", parent="Low Values")

    gb.configure_column("%_vs_1W", header_name="vs 1W %", parent="% Change")
    gb.configure_column("%_vs_1M", header_name="vs 1M %", parent="% Change")
    gb.configure_column("%_vs_2M", header_name="vs 2M %", parent="% Change")

    # Enable export + search + auto-size
    gb.configure_grid_options(
        domLayout="normal",
        enableRangeSelection=True,
        suppressRowClickSelection=False,
        quickFilter=True  # 🔍 enables global search
    )
    gb.configure_side_bar()
    grid_options = gb.build()
    grid_options["defaultColDef"]["flex"] = 1
    grid_options["enableExport"] = True

    # --- Search box ---
    search_query = st.text_input("🔍 Search Symbol:", "")

    # Pass filter to AgGrid
    grid_options["quickFilterText"] = search_query

    # --- Render ---
    st.subheader("📋 Market Stats (Grouped, Sortable, Styled, Exportable, Searchable)")
    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        theme="balham",
        height=600,
        reload_data=True,
        update_mode=GridUpdateMode.NO_UPDATE,
    )

    # Extra CSV Export Button
    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="crypto_dashboard.csv",
        mime="text/csv"
    )

else:
    st.error("No data available. Check coins.json or Bitget symbols.")
