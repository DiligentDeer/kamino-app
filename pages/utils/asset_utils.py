import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pandas.api.types import is_numeric_dtype, is_object_dtype
from src.database import (
    get_max_position_timestamp, 
    get_asset_positions, 
    get_debt_distribution, 
    get_collateral_distribution
)

def filter_dataframe(df: pd.DataFrame, key_suffix: str) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns
    """
    modify = st.toggle("Filter Data Table", key=f"toggle_filter_{key_suffix}")
    if not modify:
        return df

    df = df.copy()

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns, key=f"multiselect_{key_suffix}")
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 20 unique values as categorical
            if is_object_dtype(df[column]) and df[column].nunique() < 50:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    sorted(list(df[column].unique())),
                    default=[],
                    placeholder="Select values to filter (empty = all)",
                    key=f"filter_{column}_{key_suffix}"
                )
                if user_cat_input:
                    df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                    key=f"filter_{column}_{key_suffix}"
                )
                df = df[df[column].between(*user_num_input)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                    key=f"filter_{column}_{key_suffix}"
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input, case=False, na=False)]

    return df

@st.cache_data(ttl=300)
def load_market_data(market_name, asset_symbol, max_ts):
    if max_ts is None:
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_pos = get_asset_positions(max_ts, market_name, asset_symbol)
    df_debt = get_debt_distribution(max_ts, market_name, asset_symbol)
    df_collat = get_collateral_distribution(max_ts, market_name, asset_symbol)
    
    return max_ts, df_pos, df_debt, df_collat

def render_market_section(market_name, asset_symbol, toggle_key):
    if st.toggle(f"Show {market_name} Market Data", key=toggle_key):
        with st.container(border=True):
            col1, col2 = st.columns([0.8, 0.2])
            with col2:
                if st.button("Clear Cache & Refresh", key=f"refresh_{market_name}_{asset_symbol}"):
                    st.cache_data.clear()
                    st.rerun()

            with st.spinner(f"Loading {market_name} Market data..."):
                # Always fetch the latest timestamp first to ensure data freshness
                current_ts = get_max_position_timestamp()
                ts, df_pos, df_debt, df_collat = load_market_data(market_name, asset_symbol, current_ts)
            
            if ts:
                # Convert timestamp to readable format
                ts_dt = datetime.fromtimestamp(ts)
                st.caption(f"Data Timestamp: {ts_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                # Row 1: Debt distribution backed by [ASSET] collateral
                row1_query = f"""
                SELECT supply_symbol, SUM(supply_value) as supply_value, borrow_symbol, SUM(borrow_value) as borrow_value
                FROM quant__kamino_user_position_split 
                WHERE lending_market_name = '{market_name}' AND supply_symbol = '{asset_symbol}' AND "timestamp" = {ts}
                GROUP BY borrow_symbol, supply_symbol
                """

                st.subheader(f"Debt distribution backed by {asset_symbol} collateral", help=f"Shows which assets are being borrowed by users who have supplied {asset_symbol} as collateral. 'Active Collateral Value' is the total value of {asset_symbol} securing these loans. 'LTV' represents the aggregate Loan-to-Value ratio for these specific positions.")
                
                # Calculate metrics for Debt Distribution
                if not df_debt.empty:
                    active_collateral_value = df_debt['supply_value'].sum()
                    borrow_value_debt = df_debt['borrow_value'].sum()
                    ltv_debt = (borrow_value_debt / active_collateral_value) * 100 if active_collateral_value > 0 else 0
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Active Collateral Value", f"${active_collateral_value:,.2f}", help=f"Total value of {asset_symbol} used as collateral for the debts shown below.")
                    m2.metric("Borrow Value", f"${borrow_value_debt:,.2f}", help="Total value of assets borrowed against the active collateral.")
                    m3.metric("LTV", f"{ltv_debt:.2f}%", help="Aggregate Loan-to-Value ratio: (Total Borrow Value / Active Collateral Value) * 100.")

                
                if not df_debt.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        # Group slices < 2.5% into "Others"
                        total_supply = df_debt['supply_value'].sum()
                        if total_supply > 0:
                            mask = df_debt['supply_value'] / total_supply < 0.025
                            others_value = df_debt.loc[mask, 'supply_value'].sum()
                            df_debt_pie = df_debt[~mask].copy()
                            if others_value > 0:
                                new_row = pd.DataFrame([{'borrow_symbol': 'Others', 'supply_value': others_value}])
                                df_debt_pie = pd.concat([df_debt_pie, new_row], ignore_index=True)
                        else:
                            df_debt_pie = df_debt

                        fig1 = px.pie(df_debt_pie, values='supply_value', names='borrow_symbol', 
                                      title='% of supply_value per borrow_symbol')
                        st.plotly_chart(fig1, use_container_width=True)
                    with c2:
                        # Top 15 only
                        df_debt_sorted = df_debt.sort_values(by='supply_value', ascending=False).head(15)
                        fig2 = px.bar(df_debt_sorted, x='borrow_symbol', y='supply_value', 
                                      title='Absolute supply_value per borrow_symbol (Top 15)')
                        st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No debt distribution data available.")

                st.divider()

                # Row 2: Collateral distribution backing [ASSET] debt
                row2_query = f"""
                SELECT borrow_symbol, SUM(borrow_value) as borrow_value, supply_symbol, SUM(supply_value) as supply_value
                FROM quant__kamino_user_position_split 
                WHERE lending_market_name = '{market_name}' AND borrow_symbol = '{asset_symbol}' AND "timestamp" = {ts}
                GROUP BY supply_symbol, borrow_symbol
                """

                st.subheader(f"Collateral distribution backing {asset_symbol} debt", help=f"Shows which assets are being used as collateral by users who have borrowed {asset_symbol}. 'Collateral Value' is the total value of these assets. 'Total Borrow' is the amount of {asset_symbol} borrowed against them.")

                # Calculate metrics for Collateral Distribution
                if not df_collat.empty:
                    collateral_value_collat = df_collat['supply_value'].sum()
                    total_borrow_collat = df_collat['borrow_value'].sum()
                    ltv_collat = (total_borrow_collat / collateral_value_collat) * 100 if collateral_value_collat > 0 else 0
                    
                    m4, m5, m6 = st.columns(3)
                    m4.metric("Collateral Value", f"${collateral_value_collat:,.2f}", help="Total value of assets serving as collateral for the borrowed amount.")
                    m5.metric("Total Borrow", f"${total_borrow_collat:,.2f}", help=f"Total value of {asset_symbol} borrowed against the shown collateral.")
                    m6.metric("LTV", f"{ltv_collat:.2f}%", help="Aggregate Loan-to-Value ratio: (Total Borrow Value / Collateral Value) * 100.")

                
                
                if not df_collat.empty:
                    c3, c4 = st.columns(2)
                    with c3:
                        # Group slices < 2.5% into "Others"
                        total_borrow = df_collat['borrow_value'].sum()
                        if total_borrow > 0:
                            mask = df_collat['borrow_value'] / total_borrow < 0.025
                            others_value = df_collat.loc[mask, 'borrow_value'].sum()
                            df_collat_pie = df_collat[~mask].copy()
                            if others_value > 0:
                                new_row = pd.DataFrame([{'supply_symbol': 'Others', 'borrow_value': others_value}])
                                df_collat_pie = pd.concat([df_collat_pie, new_row], ignore_index=True)
                        else:
                            df_collat_pie = df_collat

                        fig3 = px.pie(df_collat_pie, values='borrow_value', names='supply_symbol', 
                                      title='% of borrow_value per supply_symbol')
                        st.plotly_chart(fig3, use_container_width=True)
                    with c4:
                        # Top 15 only
                        df_collat_sorted = df_collat.sort_values(by='borrow_value', ascending=False).head(15)
                        fig4 = px.bar(df_collat_sorted, x='supply_symbol', y='borrow_value', 
                                      title='Absolute borrow_value per supply_symbol (Top 15)')
                        st.plotly_chart(fig4, use_container_width=True)
                else:
                    st.info("No collateral distribution data available.")

                st.divider()

            if not df_pos.empty:
                df_filtered = filter_dataframe(df_pos, key_suffix=f"{market_name}_{asset_symbol}")
                st.subheader("Position Details", help="Detailed list of user positions corresponding to the above analysis. You can filter this table using the options above.")
                st.dataframe(
                    df_filtered.style.format({
                        "supply_value": "{:,.2f}",
                        "borrow_value": "{:,.2f}"
                    }),
                    column_config={
                        "owner": st.column_config.TextColumn("Owner Address"),
                        "obligation_id": st.column_config.TextColumn("Obligation ID"),
                    },
                    use_container_width=True
                )
            else:
                st.info(f"No positions found for {market_name} Market.")
