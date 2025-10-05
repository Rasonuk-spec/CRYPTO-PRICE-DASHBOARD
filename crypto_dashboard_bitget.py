import streamlit as st
import pandas as pd
import ccxt
import json
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Crypto Dashboard — Averages & % Change", layout="wide")
st_autorefresh(interval=300000, key="crypto_refresh")

# Load coin list
with open("coins.json") as f:
    COINS = json.load(f)

exchange = ccxt.bitget({"enableRateLimit": True})
st.title("📊 Crypto Dashboard — Multi-Period Averages, Highs, Lows & % Change")

def fetch_ohlcv(symbol, timeframe="1d", limit=1500):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception:
        return None

def compute_stats(symbol):
    df = fetch_ohlcv(symbol, timeframe="1d", limit=1500)
    if df is None or df.empty:
        return None

    current = df["close"].iloc[-1]
    periods = {"24H": 1, "3D": 3, "1W": 7, "1M": 30, "2M": 60, "6M": 180}
    stats = {"Symbol": symbol.replace("/USDT", ""), "Current": current}

    for label, days in periods.items():
        if len(df) >= days:
            subset = df.tail(days)
            high = subset["high"].max()
            low = subset["low"].min()
            avg = subset["close"].mean()
            pct = ((high - low) / low) * 100
            stats[f"Avg_{label}"] = avg
            stats[f"High_{label}"] = high
            stats[f"Low_{label}"] = low
            stats[f"Change_{label}"] = pct
        else:
            stats[f"Avg_{label}"] = stats[f"High_{label}"] = stats[f"Low_{label}"] = stats[f"Change_{label}"] = None

    stats["Ever_Avg"] = df["close"].mean()
    stats["Ever_High"] = df["high"].max()
    stats["Ever_Low"] = df["low"].min()
    return stats

results = []
for coin in COINS:
    data = compute_stats(coin.replace("USDT", "/USDT"))
    if data:
        results.append(data)

if not results:
    st.error("No data available. Please check your internet connection or coins.json.")
else:
    df = pd.DataFrame(results)
    # 🔽 Sort by 3-Day % Change descending
    df = df.sort_values(by="Change_3D", ascending=False)

    # --- Build HTML Table ---
    html = """
    <style>
    table {
        border-collapse: collapse;
        width: 100%;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    th, td {
        border: 1px solid #444;
        padding: 6px 10px;
        text-align: right;
    }
    th {
        position: sticky;
        top: 0;
        background: #111827;
        color: white;
        z-index: 2;
    }
    tr:nth-child(even) {background-color: #1e293b;}
    tr:nth-child(odd) {background-color: #0f172a;}
    td:first-child, th:first-child {
        position: sticky;
        left: 0;
        background: #111827;
        color: #fff;
        text-align: left;
        z-index: 3;
    }
    /* Separate duration groups clearly */
    td.group_end, th.group_end {
        border-right: 3px solid #999;
    }
    </style>
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Current</th>
          <th>Ever Avg</th><th>Ever High</th><th>Ever Low</th>
          <th>Avg 24H</th><th>High 24H</th><th>Low 24H</th><th class="group_end">%Ch 24H</th>
          <th>Avg 3D</th><th>High 3D</th><th>Low 3D</th><th class="group_end">%Ch 3D</th>
          <th>Avg 1W</th><th>High 1W</th><th>Low 1W</th><th class="group_end">%Ch 1W</th>
          <th>Avg 1M</th><th>High 1M</th><th>Low 1M</th><th class="group_end">%Ch 1M</th>
          <th>Avg 2M</th><th>High 2M</th><th>Low 2M</th><th class="group_end">%Ch 2M</th>
          <th>Avg 6M</th><th>High 6M</th><th>Low 6M</th><th class="group_end">%Ch 6M</th>
        </tr>
      </thead>
      <tbody>
    """

    for _, row in df.iterrows():
        html += f"""
        <tr>
          <td>{row['Symbol']}</td>
          <td>{row['Current']:.4f}</td>
          <td>{row['Ever_Avg']:.4f}</td><td>{row['Ever_High']:.4f}</td><td>{row['Ever_Low']:.4f}</td>
          <td>{row['Avg_24H']:.4f}</td><td>{row['High_24H']:.4f}</td><td>{row['Low_24H']:.4f}</td><td class="group_end">{row['Change_24H']:.2f}%</td>
          <td>{row['Avg_3D']:.4f}</td><td>{row['High_3D']:.4f}</td><td>{row['Low_3D']:.4f}</td><td class="group_end">{row['Change_3D']:.2f}%</td>
          <td>{row['Avg_1W']:.4f}</td><td>{row['High_1W']:.4f}</td><td>{row['Low_1W']:.4f}</td><td class="group_end">{row['Change_1W']:.2f}%</td>
          <td>{row['Avg_1M']:.4f}</td><td>{row['High_1M']:.4f}</td><td>{row['Low_1M']:.4f}</td><td class="group_end">{row['Change_1M']:.2f}%</td>
          <td>{row['Avg_2M']:.4f}</td><td>{row['High_2M']:.4f}</td><td>{row['Low_2M']:.4f}</td><td class="group_end">{row['Change_2M']:.2f}%</td>
          <td>{row['Avg_6M']:.4f}</td><td>{row['High_6M']:.4f}</td><td>{row['Low_6M']:.4f}</td><td class="group_end">{row['Change_6M']:.2f}%</td>
        </tr>
        """

    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)
    st.download_button("📥 Download CSV", df.to_csv(index=False).encode("utf-8"), file_name="crypto_avg_change_table.csv")
