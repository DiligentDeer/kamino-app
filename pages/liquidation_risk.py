import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import get_max_position_timestamp, get_liquidation_risk_data

# @st.cache_data(ttl=300)
def load_data(timestamp, market, asset):
    return get_liquidation_risk_data(timestamp, market, asset)

def liquidation_risk():
    st.header("Liquidation Risk")

    # Top Level Filters
    c1, c2 = st.columns(2)
    with c1:
        market = st.selectbox("Select Market", ["Main", "JLP", "Maple"])
    with c2:
        asset = st.selectbox("Filter Asset", ["PYUSD", "USDC"])

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
    st.subheader("Supply Side Risk Analysis")
    st.markdown("Filter by Supply Symbol, analyze impact of Collateral Price Shock.")

    supply_symbols = sorted(df['supply_symbol'].unique())
    selected_supply = st.multiselect(
        "Select Supply Symbols", 
        supply_symbols, 
        default=supply_symbols[:1] if supply_symbols else None
    )

    if selected_supply:
        # Filter
        df_supply = df[df['supply_symbol'].isin(selected_supply)].copy()
        
        # Drop rows with NaN shock values
        df_supply = df_supply.dropna(subset=['collateral_liquidation_price_shock'])

        # Round shock to 4 decimal places for aggregation (0.01% precision) to reduce points and aggregate
        df_supply['shock_rounded'] = df_supply['collateral_liquidation_price_shock'].round(4)
        
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
    st.subheader("Borrow Side Risk Analysis")
    st.markdown("Filter by Borrow Symbol, analyze impact of Borrow Price Shock.")

    borrow_symbols = sorted(df['borrow_symbol'].unique())
    selected_borrow = st.multiselect(
        "Select Borrow Symbols", 
        borrow_symbols, 
        default=borrow_symbols[:1] if borrow_symbols else None
    )

    if selected_borrow:
        # Filter
        df_borrow = df[df['borrow_symbol'].isin(selected_borrow)].copy()
        
        # Drop rows with NaN shock values
        df_borrow = df_borrow.dropna(subset=['borrow_liquidation_price_shock'])

        # Round shock to 4 decimal places for aggregation
        df_borrow['shock_rounded'] = df_borrow['borrow_liquidation_price_shock'].round(4)
        
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
