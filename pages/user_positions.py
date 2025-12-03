import streamlit as st
import pandas as pd
from src.database import get_max_position_timestamp, get_pyusd_main_positions

def user_positions():
    st.title("User Positions")
    
    @st.cache_data(ttl=300)
    def load_data():
        max_ts = get_max_position_timestamp()
        if max_ts is None:
            return None, pd.DataFrame()
        
        df = get_pyusd_main_positions(max_ts)
        return max_ts, df

    with st.spinner("Loading user positions..."):
        max_ts, df = load_data()
    
    if max_ts:
        # Convert timestamp to readable format if it's a unix timestamp
        try:
            ts_readable = pd.to_datetime(max_ts, unit='s', utc=True) if max_ts > 1e10 else pd.to_datetime(max_ts, utc=True)
            st.write(f"**Latest Data Timestamp:** {ts_readable}")
        except:
            st.write(f"**Latest Data Timestamp:** {max_ts}")
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No user positions found for Main market involving PYUSD.")
