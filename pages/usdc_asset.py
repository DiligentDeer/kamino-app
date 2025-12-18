import streamlit as st
from pages.utils.asset_utils import render_market_section

def usdc_asset():
    st.title("USDC across Markets", help="Aggregated view of USDC positions across different Kamino markets (Main, JLP, Maple).")
    st.write("User positions involving USDC across different markets.")

    # --- Render Sections ---
    render_market_section("Main", "USDC", "toggle_main_usdc")
    render_market_section("JLP", "USDC", "toggle_jlp_usdc")
    render_market_section("Maple", "USDC", "toggle_maple_usdc")
