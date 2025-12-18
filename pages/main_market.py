import streamlit as st
from pages.utils.market_utils import render_market_details
from pages.mappings.markets import MARKET_CONFIGS

CONFIG = MARKET_CONFIGS["MAIN"]

def main_market():
    render_market_details(CONFIG["name"], CONFIG["lending_market"], CONFIG["reserves"]["PYUSD"], "PYUSD")
