import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from pages.utils.market_utils import fetch_market_history
from pages.mappings.markets import MARKET_CONFIGS

# Construct MARKETS list from configuration
MARKETS = [
    {
        "name": cfg["name"],
        "lending_market": cfg["lending_market"],
        "reserve": cfg["reserves"]["PYUSD"],
        "page_title": cfg["page_title"],
        "page_path": cfg["page_path"]
    }
    for cfg in MARKET_CONFIGS.values()
    if "PYUSD" in cfg["reserves"]
]

def process_market_data(history):
    if not history:
        return None
        
    rows = []
    for h in history:
        ts = h.get("timestamp")
        m = h.get("metrics", {})
        rows.append({
            "timestamp": ts,
            "totalSupply": m.get("totalSupply"),
            "totalBorrows": m.get("totalBorrows"),
            "reserveBorrowLimit": m.get("reserveBorrowLimit"),
            "reserveDepositLimit": m.get("reserveDepositLimit"),
            "decimals": m.get("decimals")
        })
    
    df = pd.DataFrame(rows)
    if df.empty:
        return None
        
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    
    # Convert numeric columns
    for c in ["totalSupply", "totalBorrows", "reserveBorrowLimit", "reserveDepositLimit"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        
    df["decimals"] = pd.to_numeric(df["decimals"], errors="coerce")
    
    # Scale values
    latest_decimals = df["decimals"].iloc[-1]
    scale = 10 ** (latest_decimals if pd.notnull(latest_decimals) else 6) # Default to 6 if missing
    
    for c in ["reserveBorrowLimit", "reserveDepositLimit"]:
        df[c] = df[c] / scale

    # Sort by timestamp
    df = df.sort_values("timestamp")
    
    latest = df.iloc[-1]
    last_t = latest["timestamp"]
    
    def get_val_at_days_ago(days, col):
        target = last_t - timedelta(days=days)
        # Find nearest row before or at target
        sub = df.loc[df["timestamp"] <= target]
        if not sub.empty:
            return sub.iloc[-1][col]
        return None

    metrics = {
        "supply": {
            "current": latest["totalSupply"],
            "1d": get_val_at_days_ago(1, "totalSupply"),
            "7d": get_val_at_days_ago(7, "totalSupply"),
            "30d": get_val_at_days_ago(30, "totalSupply"),
            "cap": latest["reserveDepositLimit"]
        },
        "borrow": {
            "current": latest["totalBorrows"],
            "1d": get_val_at_days_ago(1, "totalBorrows"),
            "7d": get_val_at_days_ago(7, "totalBorrows"),
            "30d": get_val_at_days_ago(30, "totalBorrows"),
            "cap": latest["reserveBorrowLimit"]
        }
    }
    
    # Utilization
    def calc_util(bor, sup):
        if pd.notnull(bor) and pd.notnull(sup) and sup != 0:
            return bor / sup
        return 0.0

    metrics["utilization"] = {
        "current": calc_util(metrics["borrow"]["current"], metrics["supply"]["current"]),
        "1d": calc_util(metrics["borrow"]["1d"], metrics["supply"]["1d"]),
        "7d": calc_util(metrics["borrow"]["7d"], metrics["supply"]["7d"]),
        "30d": calc_util(metrics["borrow"]["30d"], metrics["supply"]["30d"]),
        "cap": 1.0 # 100%
    }
    
    return metrics

def format_change(current, past, is_percent=False):
    if pd.isna(current) or pd.isna(past) or past == 0:
        return "N/A"
    
    if is_percent:
        # For utilization (which is already a %), we show percentage point difference? 
        # Or % change of the %? Usually pp is clearer for utilization, but let's stick to % change for uniformity unless it's weird.
        # Let's do % change relative to the past value.
        diff = (current - past) / past
    else:
        diff = (current - past) / past
        
    color = "green" if diff >= 0 else "red"
    sign = "+" if diff >= 0 else ""
    return f":{color}[{sign}{diff:.1%}]"

def markets_overview():
    st.title("Markets Overview", help="High-level summary of all Kamino markets supported in this dashboard.")
    
    # Prepare dates for API fetch
    NOW = datetime.now(timezone.utc)
    START = NOW - timedelta(days=31)
    end_str = NOW.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    start_str = START.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    # Iterate over markets
    for market in MARKETS:
        with st.container(border=True):
            # Header with Button
            c_title, c_btn = st.columns([0.85, 0.15])
            with c_title:
                st.subheader(market["name"])
            with c_btn:
                if st.button("View Details", key=f"btn_{market['name']}"):
                    st.switch_page(st.Page(market["page_path"], title=market["page_title"]))

            # Fetch Data
            data = fetch_market_history(market["lending_market"], market["reserve"], start_str, end_str)
            hist = data.get("history", [])
            
            metrics = process_market_data(hist)
            
            if metrics:
                c1, c2, c3 = st.columns(3)
                
                # --- Supply ---
                with c1:
                    m = metrics["supply"]
                    st.write("Supply vs Cap")
                    ratio = m["current"] / m["cap"] if m["cap"] > 0 else 0
                    st.progress(min(ratio, 1.0))
                    
                    # Current / Cap Label
                    st.markdown(f"**{m['current']:,.0f}** / {m['cap']:,.0f} PYUSD")
                    
                    # Historical Changes
                    chg_1d = format_change(m["current"], m["1d"])
                    chg_7d = format_change(m["current"], m["7d"])
                    chg_30d = format_change(m["current"], m["30d"])
                    
                    st.caption(f"1D: {chg_1d} &nbsp; 7D: {chg_7d} &nbsp; 30D: {chg_30d}")

                # --- Borrow ---
                with c2:
                    m = metrics["borrow"]
                    st.write("Borrow vs Cap")
                    ratio = m["current"] / m["cap"] if m["cap"] > 0 else 0
                    st.progress(min(ratio, 1.0))
                    
                    st.markdown(f"**{m['current']:,.0f}** / {m['cap']:,.0f} PYUSD")
                    
                    chg_1d = format_change(m["current"], m["1d"])
                    chg_7d = format_change(m["current"], m["7d"])
                    chg_30d = format_change(m["current"], m["30d"])
                    
                    st.caption(f"1D: {chg_1d} &nbsp; 7D: {chg_7d} &nbsp; 30D: {chg_30d}")

                # --- Utilization ---
                with c3:
                    m = metrics["utilization"]
                    st.write("Utilization")
                    ratio = m["current"] # Cap is 1.0
                    st.progress(min(ratio, 1.0))
                    
                    st.markdown(f"**{m['current']:.2%}**")
                    
                    chg_1d = format_change(m["current"], m["1d"], is_percent=True)
                    chg_7d = format_change(m["current"], m["7d"], is_percent=True)
                    chg_30d = format_change(m["current"], m["30d"], is_percent=True)
                    
                    st.caption(f"1D: {chg_1d} &nbsp; 7D: {chg_7d} &nbsp; 30D: {chg_30d}")

            else:
                st.warning("No data available for this market.")
