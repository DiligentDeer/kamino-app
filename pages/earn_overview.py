import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
from pages.mappings.markets import get_market_name, PYUSD_RESERVE_MAPPING
from pages.utils.ui_components import render_delta_bubbles


def earn_overview():
    st.title("Earn Overview", help="Overview of the Sentora PYUSD Earn Vault performance, including TVL, APY, and asset allocation across markets.")
    st.write("Overview of earning opportunities and performance metrics.")
    EARN_VAULT_ID = (
        "A2wsxhA7pF4B2UKVfXocb6TAAP9ipfPJam6oMKgDE5BK"
    )
    NOW = datetime.now(timezone.utc)
    START = NOW - timedelta(days=31)
    end_str = NOW.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    start_str = START.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @st.cache_data(ttl=600, show_spinner=False)
    def fetch_allocation_transactions(vault_id: str):
        url = (
            "https://api.kamino.finance/kvaults/"
            + vault_id
            + "/allocation-transactions"
        )
        last_err = None
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=(10, 60))
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last_err = e
        st.warning(f"Failed to fetch allocation transactions after 3 attempts: {last_err}")
        return []

    @st.cache_data(ttl=600, show_spinner=False)
    def fetch_metrics_history(vault_id: str, start: str, end: str):
        base = "https://api.kamino.finance/kvaults/"
        url = (
            base
            + vault_id
            + "/metrics/history?start="
            + start
            + "&end="
            + end
        )
        last_err = None
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=(10, 60))
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last_err = e
        st.warning(f"Failed to fetch metrics history after 3 attempts: {last_err}")
        return []

    st.divider()

    st.subheader("Sentora PYUSD Earn Vault Metrics", help="Key performance indicators for the Sentora PYUSD Earn Vault, aggregated from all underlying markets.")

    with st.container():
        with st.spinner("Loading metrics..."):
            metrics = fetch_metrics_history(EARN_VAULT_ID, start_str, end_str)
        if isinstance(metrics, list) and len(metrics) > 0:
            mdf = pd.DataFrame(metrics)
            mdf["timestamp"] = pd.to_datetime(
                mdf["timestamp"], errors="coerce", utc=True
            )
            keep_cols = [
                "timestamp",
                "tvl",
                "apyActual",
                "apyFarmRewards",
                "apyReservesIncentives",
                "apyIncentives",
                "reserves",
                "vaultRewards",
            ]
            mdf = mdf[keep_cols].copy()
            for c in [
                "tvl",
                "apyActual",
                "apyFarmRewards",
                "apyReservesIncentives",
                "apyIncentives",
            ]:
                mdf[c] = pd.to_numeric(mdf[c], errors="coerce")

            r = mdf[["timestamp", "tvl", "reserves"]].copy()
            r = r.explode("reserves").dropna(subset=["reserves"])
            r["reserve_pubkey"] = r["reserves"].apply(lambda x: x.get("pubkey"))
            r["allocationRatio"] = r["reserves"].apply(
                lambda x: pd.to_numeric(x.get("allocationRatio"), errors="coerce")
            )
            r["lendingMarket"] = r["reserve_pubkey"].map(PYUSD_RESERVE_MAPPING)
            r["lendingMarketName"] = r["lendingMarket"].map(get_market_name)
            r["allocation"] = r["tvl"] * r["allocationRatio"].fillna(0)

            latest = mdf.sort_values("timestamp").tail(1)
            if not latest.empty:
                last_t = latest.iloc[0]["timestamp"]

                def value_at(days: int, col: str):
                    target = last_t - timedelta(days=days)
                    s = mdf.loc[mdf["timestamp"] <= target, col]
                    return s.iloc[-1] if len(s) else None

                current_tvl = float(latest.iloc[0]["tvl"]) if pd.notnull(
                    latest.iloc[0]["tvl"]
                ) else None
                tvl_1d = value_at(1, "tvl")
                tvl_7d = value_at(7, "tvl")
                tvl_30d = value_at(30, "tvl")

                apy_sum = (
                    latest.iloc[0]["apyActual"]
                    + latest.iloc[0]["apyFarmRewards"]
                    + latest.iloc[0]["apyReservesIncentives"]
                    + latest.iloc[0]["apyIncentives"]
                )

                def apy_at(days: int):
                    target = last_t - timedelta(days=days)
                    row = mdf.loc[mdf["timestamp"] <= target].tail(1)
                    if row.empty:
                        return None
                    return (
                        row.iloc[0]["apyActual"]
                        + row.iloc[0]["apyFarmRewards"]
                        + row.iloc[0]["apyReservesIncentives"]
                        + row.iloc[0]["apyIncentives"]
                    )

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Current TVL", f"{current_tvl:,.0f}", help="Total Value Locked in the Earn Vault. Represents the sum of all assets managed by the vault.")
                    render_delta_bubbles([
                        ("1D", None if tvl_1d is None else (current_tvl - tvl_1d)),
                        ("7D", None if tvl_7d is None else (current_tvl - tvl_7d)),
                        ("30D", None if tvl_30d is None else (current_tvl - tvl_30d)),
                    ], percent=False)
                with c2:
                    st.write("")

                apy_1d = apy_at(1)
                apy_7d = apy_at(7)
                apy_30d = apy_at(30)
                with c3:
                    st.metric("Current APY", f"{apy_sum:.2%}", help="Current Annual Percentage Yield, including lending interest and all incentives (Farm, Reserves, etc.).")
                    render_delta_bubbles([
                        ("1D", None if apy_1d is None else (apy_sum - apy_1d)),
                        ("7D", None if apy_7d is None else (apy_sum - apy_7d)),
                        ("30D", None if apy_30d is None else (apy_sum - apy_30d)),
                    ], percent=True)
                with c4:
                    st.write("")

            st.divider()
            
            st.subheader("Current Allocation by Market", help="Breakdown of how the vault's assets are distributed across different lending markets.")
            markets = [
                m for m in r["lendingMarketName"].dropna().unique().tolist()
            ]
            if markets:
                cols_alloc = st.columns(min(3, len(markets)))
                for i, m in enumerate(markets[: len(cols_alloc)]):
                    rm = r[r["lendingMarketName"] == m].sort_values("timestamp")
                    if rm.empty:
                        continue
                    last_row = rm.tail(1).iloc[0]
                    last_t_m = last_row["timestamp"]
                    alloc_curr = float(last_row["allocation"]) if pd.notnull(last_row["allocation"]) else None
                    ratio_curr = float(last_row["allocationRatio"]) if pd.notnull(last_row["allocationRatio"]) else None
                    def prev_vals(days: int):
                        row = rm.loc[rm["timestamp"] <= last_t_m - timedelta(days=days)].tail(1)
                        if row.empty:
                            return None, None
                        return (
                            float(row.iloc[0]["allocation"]) if pd.notnull(row.iloc[0]["allocation"]) else None,
                            float(row.iloc[0]["allocationRatio"]) if pd.notnull(row.iloc[0]["allocationRatio"]) else None,
                        )
                    amt_1d, pct_1d = prev_vals(1)
                    amt_7d, pct_7d = prev_vals(7)
                    amt_30d, pct_30d = prev_vals(30)
                    with cols_alloc[i]:
                        st.metric(f"{m} Allocation", "" if alloc_curr is None else f"{alloc_curr:,.0f}", help=f"Amount of assets allocated to the {m} market.")
                        render_delta_bubbles([
                            ("1D", None if amt_1d is None else (alloc_curr - amt_1d)),
                            ("7D", None if amt_7d is None else (alloc_curr - amt_7d)),
                            ("30D", None if amt_30d is None else (alloc_curr - amt_30d)),
                        ], percent=False)
                        st.metric(f"{m} Allocation %", "" if ratio_curr is None else f"{ratio_curr:.2%}", help=f"Percentage of the vault's total assets allocated to the {m} market.")
                        render_delta_bubbles([
                            ("1D", None if pct_1d is None else (ratio_curr - pct_1d)),
                            ("7D", None if pct_7d is None else (ratio_curr - pct_7d)),
                            ("30D", None if pct_30d is None else (ratio_curr - pct_30d)),
                        ], percent=True)

            st.divider()

            # Create side-by-side columns for TVL and Net Flow charts
            col_tvl, col_flow = st.columns(2)

            with col_tvl:
                st.subheader("TVL Over Time", help="Historical Total Value Locked in the Earn Vault.")
                tvl_df = mdf[["timestamp", "tvl"]].copy().sort_values("timestamp")
                fig_tvl = px.area(tvl_df, x="timestamp", y="tvl", labels={"tvl": "TVL", "timestamp": "Time"})
                st.plotly_chart(fig_tvl, use_container_width=True)

            with col_flow:
                st.subheader(
                    "Daily Net Flow (Estimated)",
                    help="This chart shows the day-over-day change in TVL based on the same data source. It approximates net deposits and withdrawals but also includes accrued yield and price fluctuations."
                )
                # Resample to daily to get cleaner bars
                # Use 'last' to get the EOD TVL, then diff to get the change
                daily_tvl = tvl_df.set_index("timestamp")["tvl"].resample("D").last()
                daily_flow = daily_tvl.diff().reset_index()
                daily_flow.columns = ["Date", "Net Flow"]
                daily_flow = daily_flow.dropna()

                # Determine color based on positive/negative flow
                daily_flow["Type"] = daily_flow["Net Flow"].apply(
                    lambda x: "Net Deposit" if x >= 0 else "Net Withdrawal"
                )

                fig_flow = px.bar(
                    daily_flow,
                    x="Date",
                    y="Net Flow",
                    color="Type",
                    color_discrete_map={
                        "Net Deposit": "#00CC96",  # Green
                        "Net Withdrawal": "#EF553B"  # Red
                    },
                    # title="Daily Change in TVL (Proxy for Net Flows)", # Title removed as per subheader context
                    labels={"Net Flow": "Change in TVL ($)", "Date": "Date"}
                )
                fig_flow.update_layout(showlegend=True)
                st.plotly_chart(fig_flow, use_container_width=True)

            st.divider()

            st.subheader("APY Components (Stacked)", help="Breakdown of the APY into its components: Lending Interest, PYUSD Incentives, and KMNO Incentives. Smoothed for readability.")
            apy_df = mdf[[
                "timestamp",
                "apyActual",
                "apyFarmRewards",
                "apyReservesIncentives",
                "apyIncentives",
            ]].copy()
            apy_df["Lending APY"] = apy_df["apyActual"].fillna(0)
            apy_df["PYUSD Incentives"] = (
                apy_df["apyFarmRewards"].fillna(0)
                + apy_df["apyReservesIncentives"].fillna(0)
            )
            apy_df["KMNO Incentives"] = apy_df["apyIncentives"].fillna(0)
            tmp = apy_df.set_index("timestamp")[[
                "Lending APY",
                "PYUSD Incentives",
                "KMNO Incentives",
            ]]
            tmp = tmp.resample("8h").median().rolling(3, min_periods=1).median()
            for col in tmp.columns:
                upper = tmp[col].quantile(0.995)
                lower = tmp[col].quantile(0.005)
                tmp[col] = tmp[col].clip(lower=lower, upper=upper)
            apy_df = tmp.reset_index()
            cutoff = NOW - timedelta(days=28)
            apy_df = apy_df[apy_df["timestamp"] >= cutoff]
            long = apy_df.melt(
                id_vars=["timestamp"],
                value_vars=[
                    "Lending APY",
                    "PYUSD Incentives",
                    "KMNO Incentives",
                ],
                var_name="component",
                value_name="value",
            )
            fig = px.area(
                long,
                x="timestamp",
                y="value",
                color="component",
                labels={"value": "APY", "timestamp": "Time"},
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Smoothed with 8h median resample, rolling median, and mild clipping; showing last 28 days.")

            st.divider()
            
            st.subheader("Allocation Charts", help="Visual representation of how assets are distributed and how the distribution ratio has changed over time.")
            r2 = r.copy()
            r2["lendingMarketName"] = r2["lendingMarketName"].fillna("Unknown")
            c_left, c_right = st.columns(2)
            with c_left:
                fig_alloc = px.area(
                    r2,
                    x="timestamp",
                    y="allocation",
                    color="lendingMarketName",
                    title="Allocation by Market",
                    labels={
                        "allocation": "Allocation",
                        "timestamp": "Time",
                        "lendingMarketName": "Market",
                    },
                )
                st.plotly_chart(fig_alloc, use_container_width=True)
            with c_right:
                rr = r[["timestamp", "lendingMarketName", "allocationRatio"]].copy()
                rr["allocationRatio"] = rr["allocationRatio"].fillna(0)
                denom = rr.groupby("timestamp")["allocationRatio"].transform("sum")
                rr["ratio"] = rr["allocationRatio"] / denom.replace(0, pd.NA)
                fig_ratio = px.area(
                    rr,
                    x="timestamp",
                    y="ratio",
                    color="lendingMarketName",
                    title="Allocation Ratio (Normalized)",
                    labels={"ratio": "Ratio", "timestamp": "Time"},
                )
                st.plotly_chart(fig_ratio, use_container_width=True)

            
        else:
            st.write("No metrics available.")

    with st.expander("Reallocation History", expanded=False):
        st.caption("History of how funds have been moved between markets.", help="Shows the volume of funds (PYUSD) moved into and out of specific markets over time. 'Inflows' are funds moving into a market strategy, 'Outflows' are funds being withdrawn from a market strategy.")
        with st.spinner("Loading data..."):
            data = fetch_allocation_transactions(EARN_VAULT_ID)
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            df["createdOn"] = pd.to_datetime(df["createdOn"], errors="coerce", utc=True)
            df["period"] = df["createdOn"].dt.floor("8h")
            df["tokenAmount"] = pd.to_numeric(df["tokenAmount"], errors="coerce")
            df["market_in"] = df.apply(
                lambda r: r.get("toMarket")
                or r.get("destinationMarket")
                or r.get("destMarket")
                or r.get("market"),
                axis=1,
            )
            df["market_out"] = df.apply(
                lambda r: r.get("market")
                or r.get("sourceMarket")
                or r.get("fromMarket"),
                axis=1,
            )
            df["market_in_name"] = df["market_in"].map(get_market_name)
            df["market_out_name"] = df["market_out"].map(get_market_name)

            inflow_df = df[df["tokenAmount"] > 0].copy()
            inflow_df["market_name"] = inflow_df["market_in_name"]
            inflow = inflow_df.groupby(["period", "market_name"], as_index=False)["tokenAmount"].sum()

            outflow_df = df[df["tokenAmount"] < 0].copy()
            outflow_df["tokenAmount"] = outflow_df["tokenAmount"].abs()
            outflow_df["market_name"] = outflow_df["market_out_name"]
            outflow = outflow_df.groupby(["period", "market_name"], as_index=False)["tokenAmount"].sum()

            fig_in = px.bar(
                inflow,
                x="period",
                y="tokenAmount",
                color="market_name",
                barmode="relative",
                log_y=True,
                title="PYUSD Inflows by Market (8h, log scale)",
                labels={
                    "period": "Period",
                    "tokenAmount": "Amount (log scale)",
                    "market_name": "Market",
                },
            )
            st.plotly_chart(fig_in, use_container_width=True)
            fig_out = px.bar(
                outflow,
                x="period",
                y="tokenAmount",
                color="market_name",
                barmode="relative",
                log_y=True,
                title="PYUSD Outflows by Market (8h, log scale)",
                labels={
                    "period": "Period",
                    "tokenAmount": "Amount (log scale)",
                    "market_name": "Market",
                },
            )
            st.plotly_chart(fig_out, use_container_width=True)
            st.caption("Outflows aggregated by absolute magnitude; inflows show positive amounts.")
        else:
            st.write("No data available.")