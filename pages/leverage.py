import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import (
    get_max_position_timestamp, 
    get_leverage_borrowed,
    get_leverage_collateral,
    get_historic_leverage_where_asset_is_collateral,
    get_historic_leverage_where_asset_is_borrowed
)

@st.cache_data(ttl=300)
def load_leverage_data(max_ts, market, asset, debt_threshold):
    df_borrowed = get_leverage_borrowed(max_ts, market, asset, debt_threshold)
    df_collateral = get_leverage_collateral(max_ts, market, asset, debt_threshold)
    df_hist_collateral = get_historic_leverage_where_asset_is_collateral(market, asset, debt_threshold)
    df_hist_borrowed = get_historic_leverage_where_asset_is_borrowed(market, asset, debt_threshold)
    return df_borrowed, df_collateral, df_hist_collateral, df_hist_borrowed

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
    with st.container(border=True):
        col1, col2 = st.columns([0.8, 0.2])
        with col2:
            if st.button("Clear Cache & Refresh", key="refresh_leverage"):
                st.cache_data.clear()
                st.rerun()

        with st.spinner("Loading leverage data..."):
            max_ts = get_max_position_timestamp()
            
            if max_ts:
                # Use a cached function to load data, passing timestamp to ensure freshness
                df_borrowed, df_collateral, df_hist_collateral, df_hist_borrowed = load_leverage_data(max_ts, market, asset, debt_threshold)
                
                st.markdown(f"**Data Timestamp:** {pd.to_datetime(max_ts, unit='s')}")

                # Display Tables
                st.subheader(f"Leverage Analysis for {asset} in {market} Market", help="Detailed breakdown of positions where the selected asset is either borrowed or used as collateral.")
                
                c_left, c_right = st.columns(2)
                
                with c_left:
                    st.subheader(f"Pairs where {asset} is Borrowed", help=f"List of collateral assets used to borrow {asset}. 'LTV' shows the loan-to-value ratio for these specific pairs.")
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
                    st.subheader(f"Pairs where {asset} is Collateral", help=f"List of assets borrowed against {asset} collateral. 'LTV' shows the loan-to-value ratio for these specific pairs.")
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
                
                # Historic Leverage Analysis
                st.subheader("Historic Leverage Analysis", help="Trends of Loan-to-Value (LTV) ratios over time for positions involving the selected asset.")
                
                st.subheader(f"Pairs where {asset} is Collateral (LTV over time)", help=f"Historical view of LTV ratios for loans backed by {asset}. Higher LTV indicates higher risk.")
                if not df_hist_collateral.empty:
                    # Convert timestamp to datetime
                    df_hist_collateral['timestamp'] = pd.to_datetime(df_hist_collateral['timestamp'], unit='s', utc=True)
                    
                    fig = px.line(
                        df_hist_collateral, 
                        x='timestamp', 
                        y='ltv', 
                        color='borrow_symbol',
                        title=f"{asset} Collateral LTV over Time"
                    )
                    
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="LTV",
                        xaxis=dict(showgrid=True),
                        yaxis=dict(showgrid=True, minor=dict(showgrid=True)),
                        legend_title="Borrowed Token"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No historic data found where {asset} is collateral with debt >= ${debt_threshold:,.0f}")

                st.subheader(f"Pairs where {asset} is Borrowed (LTV over time)", help=f"Historical view of LTV ratios for loans where {asset} is borrowed. Higher LTV indicates higher risk.")
                if not df_hist_borrowed.empty:
                    # Convert timestamp to datetime
                    df_hist_borrowed['timestamp'] = pd.to_datetime(df_hist_borrowed['timestamp'], unit='s', utc=True)
                    
                    fig = px.line(
                        df_hist_borrowed, 
                        x='timestamp', 
                        y='ltv', 
                        color='supply_symbol',
                        title=f"{asset} Borrowed LTV over Time"
                    )
                    
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="LTV",
                        xaxis=dict(showgrid=True),
                        yaxis=dict(showgrid=True, minor=dict(showgrid=True)),
                        legend_title="Collateral Token"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No historic data found where {asset} is borrowed with debt >= ${debt_threshold:,.0f}")

            else:
                st.error("Could not retrieve latest data timestamp.")
