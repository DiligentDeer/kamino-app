import requests
import streamlit as st


URL = "https://cdn.kamino.finance/kamino_lend_config_v3.json"
TARGET = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"

PYUSD = "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo"
KMNO = "KMNo3nJsBXfcpJTVhZcXLW7RmTwTt4GVFE7suUBo9sS"

PYUSD_RESERVE_MAPPING = {
    # Asset:Market
    "2gc9Dm1eB6UgVYFBUN9bWks6Kes9PbWSaPaa9DqyvEiN": "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF",
    "FswUCVjvfAuzHCgPDF95eLKscGsLHyJmD6hzkhq26CLe": "DxXdAyU3kCjnyggvHmY5nAwg5cRbbmdyX3npfDMjjMek",
    "92qeAka3ZzCGPfJriDXrE7tiNqfATVCAM6ZjjctR3TrS": "6WEGfej9B9wjxRs6t4BYpb9iCXd8CpTpJ8fVSNzHCC5y",
}

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