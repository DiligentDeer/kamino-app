import streamlit as st
import pandas as pd
from src.database import (
    get_max_position_timestamp, 
    get_leverage_borrowed,
    get_leverage_collateral
)

def leverage_page():
    st.title("Leverage Analysis")
    st.write("Analyze leverage positions for specific markets and assets.")

    # Input Section
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        
        with c1:
            market = st.selectbox(
                "Select Market",
                options=["Main", "JLP", "Maple"],
                index=0,
                help="Select the lending market to analyze"
            )
            
        with c2:
            asset = st.selectbox(
                "Select Asset",
                options=["PYUSD", "USDC"],
                index=0,
                help="Select the asset to analyze"
            )
            
        with c3:
            debt_threshold = st.number_input(
                "Debt Threshold ($)",
                min_value=0,
                value=100000,
                step=1000,
                help="Filter positions with debt value greater than this threshold"
            )

    # Data Loading
    with st.spinner("Loading leverage data..."):
        max_ts = get_max_position_timestamp()
        
        if max_ts:
            df_borrowed = get_leverage_borrowed(max_ts, market, asset, debt_threshold)
            df_collateral = get_leverage_collateral(max_ts, market, asset, debt_threshold)
            
            # Display Tables
            st.subheader(f"Leverage Analysis for {asset} in {market} Market")
            
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.markdown(f"**Pairs where {asset} is Borrowed**")
                if not df_borrowed.empty:
                    # Format LTV as percentage
                    df_borrowed['ltv'] = df_borrowed['ltv'].astype(float).map('{:.2%}'.format)
                    # Rename columns for better display
                    df_borrowed = df_borrowed.rename(columns={
                        'borrow_symbol': 'Borrowed Token',
                        'supply_symbol': 'Collateral Token',
                        'ltv': 'LTV'
                    })
                    st.dataframe(df_borrowed, use_container_width=True)
                else:
                    st.info(f"No positions found where {asset} is borrowed with debt >= ${debt_threshold:,.0f}")
            
            with c_right:
                st.markdown(f"**Pairs where {asset} is Collateral**")
                if not df_collateral.empty:
                    # Format LTV as percentage
                    df_collateral['ltv'] = df_collateral['ltv'].astype(float).map('{:.2%}'.format)
                    # Rename columns for better display
                    df_collateral = df_collateral.rename(columns={
                        'borrow_symbol': 'Borrowed Token',
                        'supply_symbol': 'Collateral Token',
                        'ltv': 'LTV'
                    })
                    st.dataframe(df_collateral, use_container_width=True)
                else:
                    st.info(f"No positions found where {asset} is collateral with debt >= ${debt_threshold:,.0f}")
                    
        else:
            st.error("Could not retrieve latest data timestamp.")
