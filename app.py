import streamlit as st
st.set_page_config(layout="wide")
from pages.earn_overview import earn_overview
from pages.markets_overview import markets_overview
from pages.main_market import main_market
from pages.jlp_market import jlp_market
from pages.maple_market import maple_market
from pages.ethena_market import ethena_market
from pages.assets import assets

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

assets_page = st.Page(
    assets,
    title="Assets",
    icon=":material/inventory_2:",
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

ethena_market_page = st.Page(
    ethena_market,
    title="Ethena Market",
    icon=":material/blur_on:",
)

pg = st.navigation(
    {
        "Earn": [earn_overview_page],
        "Markets": [
            markets_overview_page,
            main_market_page,
            jlp_market_page,
            maple_market_page,
            ethena_market_page,
        ],
        "Assets": [assets_page],
    }
)

pg.run()
