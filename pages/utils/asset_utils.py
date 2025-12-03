import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import (
    get_max_position_timestamp, 
    get_asset_positions, 
    get_debt_distribution, 
    get_collateral_distribution
)

@st.cache_data(ttl=300)
def load_market_data(market_name, asset_symbol):
    max_ts = get_max_position_timestamp()
    if max_ts is None:
        return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_pos = get_asset_positions(max_ts, market_name, asset_symbol)
    df_debt = get_debt_distribution(max_ts, market_name, asset_symbol)
    df_collat = get_collateral_distribution(max_ts, market_name, asset_symbol)
    
    return max_ts, df_pos, df_debt, df_collat

def render_market_section(market_name, asset_symbol, toggle_key):
    if st.toggle(f"Show {market_name} Market Data", key=toggle_key):
        with st.container(border=True):
            with st.spinner(f"Loading {market_name} Market data..."):
                ts, df_pos, df_debt, df_collat = load_market_data(market_name, asset_symbol)
            
            if ts:
                # Row 1: Debt distribution backed by [ASSET] collateral
                row1_query = f"""
                SELECT supply_symbol, SUM(supply_value) as supply_value, borrow_symbol, SUM(borrow_value) as borrow_value
                FROM quant__kamino_user_position_split 
                WHERE lending_market_name = '{market_name}' AND supply_symbol = '{asset_symbol}' AND "timestamp" = {ts}
                GROUP BY borrow_symbol, supply_symbol
                """

                st.subheader(f"Debt distribution backed by {asset_symbol} collateral", help=row1_query)
                
                # Calculate metrics for Debt Distribution
                if not df_debt.empty:
                    active_collateral_value = df_debt['supply_value'].sum()
                    borrow_value_debt = df_debt['borrow_value'].sum()
                    ltv_debt = (borrow_value_debt / active_collateral_value) * 100 if active_collateral_value > 0 else 0
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Active Collateral Value", f"${active_collateral_value:,.2f}")
                    m2.metric("Borrow Value", f"${borrow_value_debt:,.2f}")
                    m3.metric("LTV", f"{ltv_debt:.2f}%")

                
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

                st.subheader(f"Collateral distribution backing {asset_symbol} debt", help=row2_query)

                # Calculate metrics for Collateral Distribution
                if not df_collat.empty:
                    collateral_value_collat = df_collat['supply_value'].sum()
                    total_borrow_collat = df_collat['borrow_value'].sum()
                    ltv_collat = (total_borrow_collat / collateral_value_collat) * 100 if collateral_value_collat > 0 else 0
                    
                    m4, m5, m6 = st.columns(3)
                    m4.metric("Collateral Value", f"${collateral_value_collat:,.2f}")
                    m5.metric("Total Borrow", f"${total_borrow_collat:,.2f}")
                    m6.metric("LTV", f"{ltv_collat:.2f}%")

                
                
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
                st.dataframe(df_pos, use_container_width=True)
            else:
                st.info(f"No positions found for {market_name} Market.")
