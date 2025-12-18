import requests
import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600)
def fetch_liquidation_history():
    url = "https://services.defirisk.dev.sentora.com/metric/solana/kamino/liquidation/history?period=cumulative"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()

    if "metric" not in data:
        return pd.DataFrame()

    processed_data = []
    
    for item in data["metric"]:
        # Safety check for list length
        if len(item) < 6:
            continue
            
        # Extract Ticker info (Index 4)
        # Expected: [{"ticker": "XYZ"}, "MarketAddress"]
        meta_info = item[4]
        if not isinstance(meta_info, list) or len(meta_info) < 2:
            continue
            
        ticker_info = meta_info[0]
        if not isinstance(ticker_info, dict) or "ticker" not in ticker_info:
            continue
            
        ticker = ticker_info["ticker"]
        
        # Filter for PYUSD
        if ticker != "PYUSD":
            continue
            
        market_address = meta_info[1]
        
        # Extract Value (Index 5)
        # Expected: [Value, ...]
        value_info = item[5]
        if not isinstance(value_info, list) or len(value_info) < 1:
            continue
            
        value = value_info[0]
        
        # Extract Timestamp (Index 0) and Hash (Index 1)
        timestamp = item[0]
        tx_hash = item[1]
        
        processed_data.append({
            "timestamp": timestamp,
            "hash": tx_hash,
            "market_address": market_address,
            "value": value,
            "ticker": ticker
        })
        
    return pd.DataFrame(processed_data)
