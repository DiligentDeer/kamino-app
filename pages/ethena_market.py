import streamlit as st
from pages.utils.market_utils import render_market_details

# Ethena Market
MARKET_ADDRESS = "BJnbcRHqvppTyGesLzWASGKnmnF1wq9jZu6ExrjT7wvF"
# TODO: Update with correct PYUSD reserve address for Ethena Market
# Using a placeholder for now to fix the import error
PYUSD_RESERVE = "Placeholder_Address_Update_Me"

def ethena_market():
    st.info("Ethena Market Page is under construction. Please update the PYUSD Reserve Address.")
    # render_market_details("Ethena Market", MARKET_ADDRESS, PYUSD_RESERVE, "PYUSD")
