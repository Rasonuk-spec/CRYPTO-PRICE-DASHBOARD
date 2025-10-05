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

# --- Fetch OHLCV ---
def fetch_ohlcv(symbol, timeframe="1d", limit=1500):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
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
        "3D": 3,
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
            stats[f"%_{label}"] = ((stats[f"H_{label}"] - stats[f"L_{label}"]) / stats[f"L_{label}"]) * 100
        else:
            stats[f"A_{label}"] = None
            stats[f"H_{label}"] = None
            stats[f"L_{label}"] = None
            stats[f"%_{label}"] = None

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

    # --- Table Layout (Ever columns right after Current)
    analysis = df[
        [
            "Symbol",
            "Current", "A_Ever", "EH", "EL",
            "A_24H", "H_24H", "L_24H", "%_24H",
            "A_3D", "H_3D", "L_3D", "%_3D",
            "A_1W", "H_1W", "L_1W", "%_1W",
            "A_1M", "H_1M", "L_1M", "%_1M",
            "A_2M", "H_2M", "L_2M", "%_2M",
            "A_6M", "H_6M", "L_6M", "%_6M",
        ]
    ].copy()

    # Sort by 24H % descending
    analysis = analysis.sort_values(by="%_24H", ascending=False)

    # --- Formatting ---
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

    def color_avg(val, current):
        try:
            val = float(val)
            current = float(current)
            color = "green" if val > current else "red"
            return f"color: {color}"
        except:
            return ""

    # --- Styling ---
    styled_df = (
        analysis.style.format(
            {col: smart_format for col in analysis.columns if not col.startswith("%_")}
        )
        .format({col: format_percent for col in analysis.columns if col.startswith("%_")})
        .apply(
            lambda row: [
                color_avg(row[col], row["Current"]) if col.startswith("A_") else ""
                for col in analysis.columns
            ],
            axis=1,
        )
        .set_table_styles(
            [
                {"selector": "thead th", "props": [("background-color", "#111827"), ("color", "white"), ("font-weight", "bold")]},
                {"selector": "th", "props": [("border", "1px solid #555")]},
                {"selector": "td", "props": [("border", "1px solid #333")]},
            ]
        )
    )

    # --- Add thicker white borders between duration groups ---
    borders = ["24H", "3D", "1W", "1M", "2M", "6M"]
    for label in borders:
        styled_df = styled_df.set_table_styles(
            [
                {
                    "selector": f"th.col_heading.level0.col{analysis.columns.get_loc('%_'+label)}",
                    "props": [("border-right", "3px solid white")],
                },
                {
                    "selector": f"td.col{analysis.columns.get_loc('%_'+label)}",
                    "props": [("border-right", "3px solid white")],
                },
            ],
            overwrite=False,
        )

    # --- Display Table ---
    st.subheader("📋 Multi-Period Averages / High / Low / % Change Table (Sorted by 24H %)")
    st.dataframe(styled_df, use_container_width=True)

    # --- Freeze first column & header ---
    st.markdown(
        """
        <style>
        [data-testid="stDataFrame"] thead tr th {
            position: sticky;
            top: 0;
            z-index: 3;
            background-color: #111827 !important;
        }
        [data-testid="stDataFrame"] tbody tr td:first-child,
        [data-testid="stDataFrame"] thead tr th:first-child {
            position: sticky;
            left: 0;
            z-index: 4;
            background-color: #111827 !important;
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
