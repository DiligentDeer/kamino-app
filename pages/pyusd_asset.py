import streamlit as st
from pages.utils.asset_utils import render_market_section

def pyusd_asset():
    st.title("PYUSD across Markets")
    st.write("User positions involving PYUSD across different markets.")

    # --- Render Sections ---
    render_market_section("Main", "PYUSD", "toggle_main_pyusd")
    render_market_section("JLP", "PYUSD", "toggle_jlp_pyusd")
    render_market_section("Maple", "PYUSD", "toggle_maple_pyusd")
