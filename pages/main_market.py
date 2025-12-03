import streamlit as st
from pages.utils.market_utils import render_market_details

PYUSD_RESERVE = "2gc9Dm1eB6UgVYFBUN9bWks6Kes9PbWSaPaa9DqyvEiN"
LEDNING_MARKET = "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF"

def main_market():
    render_market_details("Main Market", LEDNING_MARKET, PYUSD_RESERVE, "PYUSD")
