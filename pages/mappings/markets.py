import requests
import streamlit as st

# Centralized Market Configuration
# Single Source of Truth for all market addresses and names
MARKET_CONFIGS = {
    "MAIN": {
        "name": "Main Market",
        "lending_market": "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF",
        "reserves": {
            "PYUSD": "2gc9Dm1eB6UgVYFBUN9bWks6Kes9PbWSaPaa9DqyvEiN",
            # Add other assets here as needed
        },
        "page_title": "Main Market",
        "page_path": "pages/main_market.py"
    },
    "JLP": {
        "name": "JLP Market",
        "lending_market": "DxXdAyU3kCjnyggvHmY5nAwg5cRbbmdyX3npfDMjjMek",
        "reserves": {
            "PYUSD": "FswUCVjvfAuzHCgPDF95eLKscGsLHyJmD6hzkhq26CLe",
        },
        "page_title": "JLP Market",
        "page_path": "pages/jlp_market.py"
    },
    "MAPLE": {
        "name": "Maple Market",
        "lending_market": "6WEGfej9B9wjxRs6t4BYpb9iCXd8CpTpJ8fVSNzHCC5y",
        "reserves": {
            "PYUSD": "92qeAka3ZzCGPfJriDXrE7tiNqfATVCAM6ZjjctR3TrS",
        },
        "page_title": "Maple Market",
        "page_path": "pages/maple_market.py"
    }
}

# Legacy mapping for compatibility (can be deprecated later)
PYUSD_RESERVE_MAPPING = {
    cfg["reserves"]["PYUSD"]: cfg["lending_market"] 
    for cfg in MARKET_CONFIGS.values() 
    if "PYUSD" in cfg["reserves"]
}


URL = "https://cdn.kamino.finance/kamino_lend_config_v3.json"
TARGET = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"

PYUSD = "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo"
KMNO = "KMNo3nJsBXfcpJTVhZcXLW7RmTwTt4GVFE7suUBo9sS"

@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_market_name_map():
    try:
        r = requests.get(URL, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    block = data.get(TARGET)
    items = []
    if isinstance(block, dict):
        items = list(block.values())
    elif isinstance(block, list):
        items = block

    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        addr = item.get("lendingMarket") or item.get("address") or item.get("market")
        name = item.get("name") or item.get("symbol") or item.get("title")
        if addr and name:
            result[addr] = name
    return result


def get_market_name(address: str) -> str:
    return get_market_name_map().get(address, address)
