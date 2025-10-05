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
            stats[f"H_{label}"] = sub["high"].max()
            stats[f"L_{label}"] = sub["low"].min()
            stats[f"P_{label}"] = ((stats[f"H_{label}"] - stats[f"L_{label}"]) / stats[f"L_{label}"]) * 100
        else:
            stats[f"H_{label}"] = None
            stats[f"L_{label}"] = None
            stats[f"P_{label}"] = None

    # Ever high/low/average
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
            "A_Ever", "EH", "EL",  # Moved here
            "H_3D", "L_3D", "P_3D",
            "H_1W", "L_1W", "P_1W",
            "H_1M", "L_1M", "P_1M",
            "H_2M", "L_2M", "P_2M",
            "H_6M", "L_6M", "P_6M",
        ]
    ].copy()

    # Sort by 3D percentage change descending
    analysis = analysis.sort_values(by="P_3D", ascending=False)

    # --- Smart formatting ---
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

    # --- Build style ---
    styled_df = (
        analysis.style.format(
            {col: smart_format for col in analysis.columns if not col.startswith("P_")}
        )
        .format({col: format_percent for col in analysis.columns if col.startswith("P_")})
        .set_table_styles(
            [
                # Header
                {
                    "selector": "thead th",
                    "props": [
                        ("background-color", "#f0f2f6"),
                        ("color", "#000"),
                        ("font-weight", "bold"),
                        ("text-align", "center"),
                        ("border", "1px solid #ccc"),
                    ],
                },
                # Table cells
                {
                    "selector": "td",
                    "props": [
                        ("border", "1px solid #ccc"),
                        ("background-color", "#ffffff"),
                        ("color", "#000"),
                        ("text-align", "center"),
                    ],
                },
            ]
        )
    )

    # --- Section borders for readability ---
    borders = ["3D", "1W", "1M", "2M", "6M"]
    for label in borders:
        styled_df = styled_df.set_table_styles(
            [
                {
                    "selector": f"th.col_heading.level0.col{analysis.columns.get_loc('P_'+label)}",
                    "props": [("border-right", "3px solid #888")],
                },
                {
                    "selector": f"td.col{analysis.columns.get_loc('P_'+label)}",
                    "props": [("border-right", "3px solid #888")],
                },
            ],
            overwrite=False,
        )

    # --- Display Table ---
    st.subheader("📋 Multi-Period High / Low + % Change Table (Sorted by 3D % Change)")
    st.dataframe(styled_df, use_container_width=True, height=700)

    # --- Sticky header ---
    st.markdown(
        """
        <style>
        [data-testid="stDataFrame"] th {
            position: sticky;
            top: 0;
            background: #f0f2f6 !important;
            color: #000 !important;
            z-index: 2;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- CSV Export ---
    st.download_button(
        "📥 Download Analysis CSV",
        analysis.to_csv(index=False).encode("utf-8"),
        file_name="crypto_high_low_analysis.csv",
        mime="text/csv",
    )

else:
    st.error("⚠️ No data available. Check coins.json or Bitget symbols.")
