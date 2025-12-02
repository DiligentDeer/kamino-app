import streamlit as st

from src.database import some_db_query


@st.cache_data(ttl=60 * 60, show_spinner=False)
def some_db_query_cached():
    return some_db_query()
