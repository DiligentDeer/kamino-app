import streamlit as st
from pages.utils.market_utils import render_market_details

# Maple Market
MARKET_ADDRESS = "6WEGfej9B9wjxRs6t4BYpb9iCXd8CpTpJ8fVSNzHCC5y"
PYUSD_RESERVE = "92qeAka3ZzCGPfJriDXrE7tiNqfATVCAM6ZjjctR3TrS"

def maple_market():
    render_market_details("Maple Market", MARKET_ADDRESS, PYUSD_RESERVE, "PYUSD")
