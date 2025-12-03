import streamlit as st
st.set_page_config(layout="wide")
from pages.earn_overview import earn_overview
from pages.markets_overview import markets_overview
from pages.main_market import main_market
from pages.jlp_market import jlp_market
from pages.maple_market import maple_market
from pages.pyusd_asset import pyusd_asset
from pages.usdc_asset import usdc_asset
from pages.leverage import leverage_page
from pages.user_positions import user_positions

earn_overview_page = st.Page(
    earn_overview,
    title="Overview",
    icon=":material/trending_up:",
    default=True,
)

markets_overview_page = st.Page(
    markets_overview,
    title="Overview",
    icon=":material/assessment:",
)

pyusd_asset_page = st.Page(
    pyusd_asset,
    title="PYUSD",
    icon=":material/attach_money:",
)

usdc_asset_page = st.Page(
    usdc_asset,
    title="USDC",
    icon=":material/monetization_on:",
)

leverage_page_obj = st.Page(
    leverage_page,
    title="Leverage",
    icon=":material/account_balance_wallet:",
)

main_market_page = st.Page(
    main_market,
    title="Main Market",
    icon=":material/store:",
)

jlp_market_page = st.Page(
    jlp_market,
    title="JLP Market",
    icon=":material/stacked_bar_chart:",
)

maple_market_page = st.Page(
    maple_market,
    title="Maple Market",
    icon=":material/forest:",
)

user_positions_page = st.Page(
    user_positions,
    title="User Positions",
    icon=":material/list:",
)

pg = st.navigation(
    {
        "Earn": [earn_overview_page],
        "Markets": [
            markets_overview_page,
            main_market_page,
            jlp_market_page,
            maple_market_page,
        ],
        "Assets": [pyusd_asset_page, usdc_asset_page, leverage_page_obj],
        "Positions": [user_positions_page],
    }
)

pg.run()
