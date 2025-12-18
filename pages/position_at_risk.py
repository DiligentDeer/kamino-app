import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import get_position_at_risk_data, get_position_details

@st.cache_data(ttl=300)
def load_data(market, asset, threshold=1.1):
    return get_position_at_risk_data(market, asset, threshold)

@st.cache_data(ttl=300)
def load_position_details(timestamp, market, asset):
    return get_position_details(timestamp, market, asset)

def position_at_risk():
    c_header, c_refresh = st.columns([0.85, 0.15])
    with c_header:
        st.header("Position at Risk")
    with c_refresh:
        if st.button("Refresh", key="refresh_pos_risk"):
            st.cache_data.clear()
            st.rerun()

    # Top Level Filters
    c1, c2 = st.columns(2)
    with c1:
        market = st.selectbox("Select Market", ["Main", "JLP", "Maple"], key="pos_risk_market")
    with c2:
        asset = st.selectbox("Filter Asset", ["PYUSD", "USDC"], key="pos_risk_asset")

    # Load Data
    with st.spinner("Loading data..."):
        # Threshold is hardcoded to 1.1 as per request
        df = load_data(market, asset, threshold=1.1)

    if df.empty:
        st.warning("No data available for the selected parameters.")
        return

    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Latest Data
    latest_df = df.iloc[-1]
    
    st.markdown(f"**Data Timestamp:** {latest_df['timestamp']}")
    st.info("Showing metrics for positions with Health Factor <= 1.1")

    # Metric Cards
    
    # 1. Asset as Borrow
    st.subheader(f"{asset} as Borrow Asset", help=f"Metrics for positions where {asset} is being BORROWED and Health Factor <= 1.1")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Collateral at Risk", 
        f"${latest_df['asset_borrow_collateral_at_risk']:,.2f}",
        help=f"Total value of collateral in positions borrowing {asset} with HF <= 1.1"
    )
    m2.metric(
        "Debt at Risk", 
        f"${latest_df['asset_borrow_debt_at_risk']:,.2f}",
        help=f"Total value of debt in positions borrowing {asset} with HF <= 1.1"
    )
    m3.metric(
        "% Collateral at Risk", 
        f"{latest_df['asset_borrow_collateral_at_risk_pct']:.2f}%",
        help=f"Percentage of total collateral that is at risk (HF <= 1.1) for positions borrowing {asset}"
    )
    m4.metric(
        "% Debt at Risk", 
        f"{latest_df['asset_borrow_debt_at_risk_pct']:.2f}%",
        help=f"Percentage of total debt that is at risk (HF <= 1.1) for positions borrowing {asset}"
    )
    
    # 2. Asset as Supply
    st.subheader(f"{asset} as Supply Asset", help=f"Metrics for positions where {asset} is being SUPPLIED and Health Factor <= 1.1")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Collateral at Risk", 
        f"${latest_df['asset_supply_collateral_at_risk']:,.2f}",
        help=f"Total value of collateral in positions supplying {asset} with HF <= 1.1"
    )
    m2.metric(
        "Debt at Risk", 
        f"${latest_df['asset_supply_debt_at_risk']:,.2f}",
        help=f"Total value of debt in positions supplying {asset} with HF <= 1.1"
    )
    m3.metric(
        "% Collateral at Risk", 
        f"{latest_df['asset_supply_collateral_at_risk_pct']:.2f}%",
        help=f"Percentage of total collateral that is at risk (HF <= 1.1) for positions supplying {asset}"
    )
    m4.metric(
        "% Debt at Risk", 
        f"{latest_df['asset_supply_debt_at_risk_pct']:.2f}%",
        help=f"Percentage of total debt that is at risk (HF <= 1.1) for positions supplying {asset}"
    )

    st.divider()

    # Time Series Charts
    st.subheader("Risk Over Time")
    
    tab1, tab2 = st.tabs([f"{asset} as Borrow", f"{asset} as Supply"])
    
    with tab1:
        # Raw Values
        st.subheader("Raw Value at Risk", help="The total dollar amount of Collateral and Debt exposed to liquidation risk.\n\nShows how the collateral and debt at risk (HF <= 1.1) for positions borrowing " + asset + " has evolved over time.")
        fig_raw = px.line(
            df, 
            x='timestamp', 
            y=['asset_borrow_collateral_at_risk', 'asset_borrow_debt_at_risk'],
            labels={'value': 'Value ($)', 'timestamp': 'Date', 'variable': 'Metric'}
        )
        # Rename the legend items
        new_names = {'asset_borrow_collateral_at_risk': 'Collateral at Risk', 'asset_borrow_debt_at_risk': 'Debt at Risk'}
        fig_raw.for_each_trace(lambda t: t.update(name = new_names.get(t.name, t.name)))
        st.plotly_chart(fig_raw, use_container_width=True)
        
        # Percentages
        st.subheader("% Value at Risk", help="The percentage of the total market's Collateral and Debt that is exposed to liquidation risk.\n\nShows the relative risk exposure for positions borrowing " + asset + " over time.")
        fig_pct = px.line(
            df, 
            x='timestamp', 
            y=['asset_borrow_collateral_at_risk_pct', 'asset_borrow_debt_at_risk_pct'],
            labels={'value': 'Percentage (%)', 'timestamp': 'Date', 'variable': 'Metric'}
        )
        new_names_pct = {'asset_borrow_collateral_at_risk_pct': '% Collateral at Risk', 'asset_borrow_debt_at_risk_pct': '% Debt at Risk'}
        fig_pct.for_each_trace(lambda t: t.update(name = new_names_pct.get(t.name, t.name)))
        fig_pct.update_layout(yaxis_tickformat='.2f')
        st.plotly_chart(fig_pct, use_container_width=True)

    with tab2:
        # Raw Values
        st.subheader("Raw Value at Risk", help="The total dollar amount of Collateral and Debt exposed to liquidation risk.\n\nShows how the collateral and debt at risk (HF <= 1.1) for positions supplying " + asset + " has evolved over time.")
        fig_raw = px.line(
            df, 
            x='timestamp', 
            y=['asset_supply_collateral_at_risk', 'asset_supply_debt_at_risk'],
            labels={'value': 'Value ($)', 'timestamp': 'Date', 'variable': 'Metric'}
        )
        new_names = {'asset_supply_collateral_at_risk': 'Collateral at Risk', 'asset_supply_debt_at_risk': 'Debt at Risk'}
        fig_raw.for_each_trace(lambda t: t.update(name = new_names.get(t.name, t.name)))
        st.plotly_chart(fig_raw, use_container_width=True)
        
        # Percentages
        st.subheader("% Value at Risk", help="The percentage of the total market's Collateral and Debt that is exposed to liquidation risk.\n\nShows the relative risk exposure for positions supplying " + asset + " over time.")
        fig_pct = px.line(
            df, 
            x='timestamp', 
            y=['asset_supply_collateral_at_risk_pct', 'asset_supply_debt_at_risk_pct'],
            labels={'value': 'Percentage (%)', 'timestamp': 'Date', 'variable': 'Metric'}
        )
        new_names_pct = {'asset_supply_collateral_at_risk_pct': '% Collateral at Risk', 'asset_supply_debt_at_risk_pct': '% Debt at Risk'}
        fig_pct.for_each_trace(lambda t: t.update(name = new_names_pct.get(t.name, t.name)))
        fig_pct.update_layout(yaxis_tickformat='.2f')
        st.plotly_chart(fig_pct, use_container_width=True)

    st.divider()

    # Detailed Position Data Table
    st.subheader("Detailed Position Data", help="A table listing individual positions with Health Factor <= 1.1. Includes details like supply/borrow amounts and current LTV.")
    with st.spinner("Loading detailed position data..."):
        # Use the latest timestamp from the main dataframe
        latest_ts = int(latest_df['timestamp'].timestamp())
        df_details = load_position_details(latest_ts, market, asset)
    
    if not df_details.empty:
        st.dataframe(
            df_details,
            use_container_width=True,
            column_config={
                "owner": st.column_config.TextColumn("Owner"),
                "obligation_id": st.column_config.TextColumn("Obligation ID"),
                "supply_symbol": st.column_config.TextColumn("Supply Asset"),
                "supply_value": st.column_config.NumberColumn("Supply Value ($)", format="$%.2f"),
                "borrow_symbol": st.column_config.TextColumn("Borrow Asset"),
                "borrow_value": st.column_config.NumberColumn("Borrow Value ($)", format="$%.2f"),
                "health_factor": st.column_config.NumberColumn("Health Factor", format="%.4f")
            },
            hide_index=True
        )
    else:
        st.info("No detailed position data available.")
        new_names_pct = {'asset_supply_collateral_at_risk_pct': '% Collateral at Risk', 'asset_supply_debt_at_risk_pct': '% Debt at Risk'}
        fig_pct.for_each_trace(lambda t: t.update(name = new_names_pct.get(t.name, t.name)))
        fig_pct.update_layout(yaxis_tickformat='.2f')
        st.plotly_chart(fig_pct, use_container_width=True)
