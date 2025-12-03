import streamlit as st
from pages.utils.market_utils import render_market_details

# JLP Market
MARKET_ADDRESS = "DxXdAyU3kCjnyggvHmY5nAwg5cRbbmdyX3npfDMjjMek"
PYUSD_RESERVE = "FswUCVjvfAuzHCgPDF95eLKscGsLHyJmD6hzkhq26CLe"

def jlp_market():
    render_market_details("JLP Market", MARKET_ADDRESS, PYUSD_RESERVE, "PYUSD")
