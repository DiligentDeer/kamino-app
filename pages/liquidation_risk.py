import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import get_max_position_timestamp, get_liquidation_risk_data
from src.api import fetch_liquidation_history
from pages.mappings.markets import get_market_name, PYUSD_RESERVE_MAPPING

@st.cache_data(ttl=300)
def load_data(timestamp, market, asset):
    return get_liquidation_risk_data(timestamp, market, asset)

def liquidation_risk():
    c_header, c_refresh = st.columns([0.85, 0.15])
    with c_header:
        st.header("Liquidation Risk", help="Analyzes the solvency of positions under price shock scenarios. Helps identify potential liquidations if asset prices move significantly.")
    with c_refresh:
        if st.button("Refresh", key="refresh_liquidation_risk"):
            st.cache_data.clear()
            st.rerun()

    # Top Level Filters
    c1, c2 = st.columns(2)
    with c1:
        market = st.selectbox("Select Market", ["Main", "JLP", "Maple"], help="Choose the lending market environment (e.g., Main, JLP, Maple) to analyze.")
    with c2:
        asset = st.selectbox("Filter Asset", ["PYUSD", "USDC"], help="Select the specific asset (e.g., PYUSD, USDC) to filter the risk analysis.")

    # Load Data
    with st.spinner("Loading data..."):
        ts = get_max_position_timestamp()
        if ts is None:
            st.error("Could not fetch timestamp.")
            return
        
        df = load_data(ts, market, asset)

    if df.empty:
        st.warning("No data available for the selected parameters.")
        return

    st.markdown(f"**Data Timestamp:** {pd.to_datetime(ts, unit='s')}")

    # Row 1: Supply Side
    st.subheader("Supply Side Risk Analysis", help="Analyzes the potential impact of a drop in collateral asset prices. Shows the cumulative value of collateral and debt that would be at risk of liquidation at different price shock levels.")
    st.markdown("Filter by Supply Symbol, analyze impact of Collateral Price Shock.")

    supply_symbols = sorted(df['supply_symbol'].unique())
    selected_supply = st.multiselect(
        "Select Supply Symbols", 
        supply_symbols, 
        default=supply_symbols[:1] if supply_symbols else None,
        help="Select the collateral asset to analyze."
    )

    adjust_supply = st.toggle("Adjust Collateral Value by Shock", value=False, help="If enabled, Collateral Value is reduced by the shock percentage (Supply Value * (1 - Shock)). This simulates the post-shock value of the collateral.")

    if selected_supply:
        # Filter
        df_supply = df[df['supply_symbol'].isin(selected_supply)].copy()
        
        # Drop rows with NaN shock values
        df_supply = df_supply.dropna(subset=['collateral_liquidation_price_shock'])

        # Round shock to 4 decimal places for aggregation (0.01% precision) to reduce points and aggregate
        df_supply['shock_rounded'] = df_supply['collateral_liquidation_price_shock'].round(4)
        
        # Apply adjustment if toggled
        if adjust_supply:
            df_supply['supply_value'] = df_supply['supply_value'] * (1 - df_supply['shock_rounded'])

        # Aggregate by shock bucket
        df_agg_supply = df_supply.groupby('shock_rounded')[['supply_value', 'borrow_value']].sum().sort_index()
        
        # Cumulative Sums on aggregated data
        df_agg_supply['cumulative_borrow_value'] = df_agg_supply['borrow_value'].cumsum()
        df_agg_supply['cumulative_supply_value'] = df_agg_supply['supply_value'].cumsum()
        
        # Reset index to make shock_rounded a column for plotting
        df_agg_supply = df_agg_supply.reset_index()

        # Charts
        fig1 = px.line(
            df_agg_supply, 
            x='shock_rounded', 
            y=['cumulative_supply_value', 'cumulative_borrow_value'],
            title="Liquidatable Collateral & Debt vs Shock",
            labels={
                'shock_rounded': 'Collateral Price Shock', 
                'value': 'Cumulative Value',
                'variable': 'Metric'
            }
        )
        fig1.update_layout(
            xaxis_tickformat='.0%',
            xaxis=dict(
                showgrid=True, 
                gridcolor='LightGrey',
                minor=dict(showgrid=True, gridcolor='WhiteSmoke'),
                range=[None, 1]
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='LightGrey',
                minor=dict(showgrid=True, gridcolor='WhiteSmoke')
            ),
            legend_title_text=''
        )
        # Rename the legend items
        new_names = {'cumulative_supply_value': 'Liquidatable Collateral', 'cumulative_borrow_value': 'Liquidatable Debt'}
        fig1.for_each_trace(lambda t: t.update(name = new_names.get(t.name, t.name)))
        
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Please select at least one Supply Symbol.")

    st.divider()

    # Row 2: Borrow Side
    st.subheader("Borrow Side Risk Analysis", help="Analyzes the potential impact of an increase in borrowed asset prices. Shows the cumulative value of collateral and debt that would be at risk of liquidation at different price shock levels.")
    st.markdown("Filter by Borrow Symbol, analyze impact of Borrow Price Shock.")

    borrow_symbols = sorted(df['borrow_symbol'].unique())
    selected_borrow = st.multiselect(
        "Select Borrow Symbols", 
        borrow_symbols, 
        default=borrow_symbols[:1] if borrow_symbols else None,
        help="Select the borrowed asset to analyze."
    )

    adjust_borrow = st.toggle("Adjust Debt Value by Shock", value=False, help="If enabled, Debt Value is increased by the shock percentage (Borrow Value * (1 + Shock)). This simulates the post-shock value of the debt.")

    if selected_borrow:
        # Filter
        df_borrow = df[df['borrow_symbol'].isin(selected_borrow)].copy()
        
        # Drop rows with NaN shock values
        df_borrow = df_borrow.dropna(subset=['borrow_liquidation_price_shock'])

        # Round shock to 4 decimal places for aggregation
        df_borrow['shock_rounded'] = df_borrow['borrow_liquidation_price_shock'].round(4)
        
        # Apply adjustment if toggled
        if adjust_borrow:
            df_borrow['borrow_value'] = df_borrow['borrow_value'] * (1 + df_borrow['shock_rounded'])

        # Aggregate by shock bucket
        df_agg_borrow = df_borrow.groupby('shock_rounded')[['supply_value', 'borrow_value']].sum().sort_index()
        
        # Cumulative Sums on aggregated data
        df_agg_borrow['cumulative_borrow_value'] = df_agg_borrow['borrow_value'].cumsum()
        df_agg_borrow['cumulative_supply_value'] = df_agg_borrow['supply_value'].cumsum()
        
        # Reset index
        df_agg_borrow = df_agg_borrow.reset_index()

        # Charts
        fig2 = px.line(
            df_agg_borrow, 
            x='shock_rounded', 
            y=['cumulative_supply_value', 'cumulative_borrow_value'],
            title="Liquidatable Collateral & Debt vs Shock",
            labels={
                'shock_rounded': 'Borrow Price Shock', 
                'value': 'Cumulative Value',
                'variable': 'Metric'
            }
        )
        fig2.update_layout(
            xaxis_tickformat='.0%',
            xaxis=dict(
                showgrid=True, 
                gridcolor='LightGrey',
                minor=dict(showgrid=True, gridcolor='WhiteSmoke'),
                range=[None, 1.5]
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='LightGrey',
                minor=dict(showgrid=True, gridcolor='WhiteSmoke')
            ),
            legend_title_text=''
        )
        # Rename the legend items
        new_names = {'cumulative_supply_value': 'Liquidatable Collateral', 'cumulative_borrow_value': 'Liquidatable Debt'}
        fig2.for_each_trace(lambda t: t.update(name = new_names.get(t.name, t.name)))
        
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Please select at least one Borrow Symbol.")

    st.divider()
    
    with st.expander("Historical Liquidation Data (PYUSD)", expanded=False):
        st.caption("Data source: Sentora DeFi Risk API")
        st.markdown("Shows the history of cumulative liquidation values for PYUSD across different markets.", help="Data is fetched from the Sentora DeFi Risk API. Click 'Load Historical Data' to view the chart and table.")
        
        # User requested to query only if expanded. 
        # In Streamlit, we use a button to ensure data is only fetched on user request.
        if st.button("Load Historical Data", key="load_hist_data"):
            with st.spinner("Fetching historical data..."):
                hist_df = fetch_liquidation_history()
            
            if not hist_df.empty:
                # Map Reserve Address to Lending Market Address first
                hist_df['lending_market_address'] = hist_df['market_address'].map(PYUSD_RESERVE_MAPPING)
                
                # Fallback to original address if mapping not found (optional, but good for debugging)
                hist_df['lending_market_address'] = hist_df['lending_market_address'].fillna(hist_df['market_address'])
                
                # Filter out specific unwanted markets
                hist_df = hist_df[hist_df['lending_market_address'] != "D4c6nsTRjD2Kv7kYEUjtXiw72YKP8a1XHd33g38UpaV8"]
                
                # Map Lending Market Address to Market Name
                hist_df['market_name'] = hist_df['lending_market_address'].apply(get_market_name)
                
                # Convert timestamp to datetime
                hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'])
                
                # Sort by timestamp
                hist_df = hist_df.sort_values('timestamp')
                
                # Chart
                st.subheader("Liquidation Value Over Time")
                fig_hist = px.line(
                    hist_df,
                    x='timestamp',
                    y='value',
                    color='market_name',
                    title="Cumulative Liquidation Value (PYUSD)",
                    labels={'value': 'Value ($)', 'timestamp': 'Time', 'market_name': 'Market'}
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Table
                st.subheader("Data Table")
                # Show Time, Hash, Market, Value
                display_cols = ['timestamp', 'hash', 'market_name', 'value']
                st.dataframe(
                    hist_df[display_cols].sort_values('timestamp', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No historical liquidation data found for PYUSD.")
