import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta, timezone
import plotly.express as px
import plotly.graph_objects as go
from pages.utils.ui_components import fmt_compact, render_delta_bubbles

@st.cache_data(ttl=600, show_spinner=False)
def fetch_market_history(market: str, reserve: str, start: str, end: str):
    base = "https://api.kamino.finance/kamino-market/"
    url = (
        base
        + market
        + "/reserves/"
        + reserve
        + "/metrics/history?env=mainnet-beta&start="
        + start
        + "&end="
        + end
    )
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=(5, 25))
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ReadTimeout as e:
            last_err = e
        except requests.RequestException as e:
            last_err = e
    return {"history": []}

def render_market_details(market_name: str, lending_market: str, reserve_address: str, asset_name: str = "PYUSD"):
    st.title(f"{asset_name}: {market_name}")
    NOW = datetime.now(timezone.utc)
    START = NOW - timedelta(days=31)
    end_str = NOW.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    start_str = START.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    with st.spinner("Loading market metrics..."):
        data = fetch_market_history(lending_market, reserve_address, start_str, end_str)
    
    if isinstance(data, dict) and len(data.get("history", [])) == 0:
        st.warning("Market API timed out or returned no data; showing empty state.")

    hist = data.get("history", []) if isinstance(data, dict) else []
    rows = []
    for h in hist:
        ts = h.get("timestamp")
        m = h.get("metrics", {})
        rows.append(
            {
                "timestamp": ts,
                "symbol": m.get("symbol"),
                "decimals": m.get("decimals"),
                "borrowTvl": m.get("borrowTvl"),
                "depositTvl": m.get("depositTvl"),
                "borrowCurve": m.get("borrowCurve"),
                "totalSupply": m.get("totalSupply"),
                "borrowFactor": m.get("borrowFactor"),
                "totalBorrows": m.get("totalBorrows"),
                "totalLiquidity": m.get("totalLiquidity"),
                "protocolTakeRate": m.get("protocolTakeRate"),
                "borrowInterestAPY": m.get("borrowInterestAPY"),
                "supplyInterestAPY": m.get("supplyInterestAPY"),
                "reserveBorrowLimit": m.get("reserveBorrowLimit"),
                "assetOraclePriceUSD": m.get("assetOraclePriceUSD"),
                "reserveDepositLimit": m.get("reserveDepositLimit"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        for c in [
            "borrowTvl",
            "depositTvl",
            "totalSupply",
            "totalBorrows",
            "totalLiquidity",
            "borrowInterestAPY",
            "supplyInterestAPY",
            "reserveBorrowLimit",
            "reserveDepositLimit",
            "assetOraclePriceUSD",
        ]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["decimals"] = pd.to_numeric(df.get("decimals"), errors="coerce")
        scale = (10 ** df["decimals"].fillna(0)).astype(float)
        df["reserveDepositLimit"] = df["reserveDepositLimit"] / scale
        df["reserveBorrowLimit"] = df["reserveBorrowLimit"] / scale

    latest = df.sort_values("timestamp").tail(1)
    if not latest.empty:
        last_t = latest.iloc[0]["timestamp"]

        def val_at(days: int, expr: str):
            target = last_t - timedelta(days=days)
            sub = df.loc[df["timestamp"] <= target]
            if sub.empty:
                return None
            row = sub.tail(1).iloc[0]
            if expr == "supply_util":
                denom = pd.to_numeric(row["reserveDepositLimit"], errors="coerce")
                num = pd.to_numeric(row["totalSupply"], errors="coerce")
                return (num / denom) if pd.notnull(num) and pd.notnull(denom) and denom != 0 else None
            if expr == "market_util":
                denom = pd.to_numeric(row["totalSupply"], errors="coerce")
                num = pd.to_numeric(row["totalBorrows"], errors="coerce")
                return (num / denom) if pd.notnull(num) and pd.notnull(denom) and denom != 0 else None
            if expr == "borrow_cap_util":
                denom = pd.to_numeric(row["reserveBorrowLimit"], errors="coerce")
                num = pd.to_numeric(row["totalBorrows"], errors="coerce")
                return (num / denom) if pd.notnull(num) and pd.notnull(denom) and denom != 0 else None
            return row.get(expr)

        price = latest.iloc[0]["assetOraclePriceUSD"]
        status_ok = pd.notnull(price) and (0.99 <= float(price) <= 1.01)
        pill_bg = "#e6f4ea" if status_ok else "#fde8e8"
        pill_fg = "#0a0" if status_ok else "#d00"
        st.markdown(
            f"<span style='display:inline-block;padding:6px 10px;border-radius:8px;background:{pill_bg};color:{pill_fg};font-weight:600;'>"
            + ("Pegged" if status_ok else "Depeg detected")
            + ("" if not pd.notnull(price) else f" · Price {float(price):.4f}")
            + "</span>",
            unsafe_allow_html=True,
        )

        st.divider()

        c1, c2, c3, c4 = st.columns(4)
        curr_supply = latest.iloc[0]["totalSupply"]
        supply_1d = val_at(1, "totalSupply")
        supply_7d = val_at(7, "totalSupply")
        supply_30d = val_at(30, "totalSupply")
        with c1:
            st.metric(
                f"{asset_name} Supply",
                "-" if pd.isna(curr_supply) else f"{float(curr_supply):,.0f}",
                help=(
                    "Deposits TVL: "
                    + (
                        fmt_compact(latest.iloc[0]["depositTvl"]) if pd.notna(latest.iloc[0]["depositTvl"]) else "-"
                    )
                ),
            )
            render_delta_bubbles([
                ("1D", None if supply_1d is None else (float(curr_supply) - float(supply_1d))),
                ("7D", None if supply_7d is None else (float(curr_supply) - float(supply_7d))),
                ("30D", None if supply_30d is None else (float(curr_supply) - float(supply_30d))),
            ], percent=False)

        curr_supply_cap = latest.iloc[0]["reserveDepositLimit"]
        cap_1d = val_at(1, "reserveDepositLimit")
        cap_7d = val_at(7, "reserveDepositLimit")
        cap_30d = val_at(30, "reserveDepositLimit")
        with c2:
            st.metric("Supply Cap", "" if pd.isna(curr_supply_cap) else f"{float(curr_supply_cap):,.0f}")
            render_delta_bubbles([
                ("1D", None if cap_1d is None else (float(curr_supply_cap) - float(cap_1d))),
                ("7D", None if cap_7d is None else (float(curr_supply_cap) - float(cap_7d))),
                ("30D", None if cap_30d is None else (float(curr_supply_cap) - float(cap_30d))),
            ], percent=False)

        curr_supply_util = None
        if pd.notnull(curr_supply) and pd.notnull(curr_supply_cap) and float(curr_supply_cap) != 0:
            curr_supply_util = float(curr_supply) / float(curr_supply_cap)
        su_1d = val_at(1, "supply_util")
        su_7d = val_at(7, "supply_util")
        su_30d = val_at(30, "supply_util")
        with c3:
            st.metric("Supply Cap Utilization", "-" if curr_supply_util is None else f"{curr_supply_util:.2%}")
            render_delta_bubbles([
                ("1D", None if su_1d is None else (curr_supply_util - su_1d)),
                ("7D", None if su_7d is None else (curr_supply_util - su_7d)),
                ("30D", None if su_30d is None else (curr_supply_util - su_30d)),
            ], percent=True)

        curr_market_util = None
        bor = latest.iloc[0]["totalBorrows"]
        if pd.notnull(bor) and pd.notnull(curr_supply) and float(curr_supply) != 0:
            curr_market_util = float(bor) / float(curr_supply)
        mu_1d = val_at(1, "market_util")
        mu_7d = val_at(7, "market_util")
        mu_30d = val_at(30, "market_util")
        with c4:
            st.metric("Market Utilization %", "-" if curr_market_util is None else f"{curr_market_util:.2%}")
            render_delta_bubbles([
                ("1D", None if mu_1d is None else (curr_market_util - mu_1d)),
                ("7D", None if mu_7d is None else (curr_market_util - mu_7d)),
                ("30D", None if mu_30d is None else (curr_market_util - mu_30d)),
            ], percent=True)

        d1, d2, d3, d4 = st.columns(4)
        curr_borrow = latest.iloc[0]["totalBorrows"]
        b_1d = val_at(1, "totalBorrows")
        b_7d = val_at(7, "totalBorrows")
        b_30d = val_at(30, "totalBorrows")
        with d1:
            st.metric(
                f"{asset_name} Borrow",
                "-" if pd.isna(curr_borrow) else f"{float(curr_borrow):,.0f}",
                help=(
                    "Borrows TVL: "
                    + (
                        fmt_compact(latest.iloc[0]["borrowTvl"]) if pd.notna(latest.iloc[0]["borrowTvl"]) else "-"
                    )
                ),
            )
            render_delta_bubbles([
                ("1D", None if b_1d is None else (float(curr_borrow) - float(b_1d))),
                ("7D", None if b_7d is None else (float(curr_borrow) - float(b_7d))),
                ("30D", None if b_30d is None else (float(curr_borrow) - float(b_30d))),
            ], percent=False)

        curr_borrow_cap = latest.iloc[0]["reserveBorrowLimit"]
        bc_1d = val_at(1, "reserveBorrowLimit")
        bc_7d = val_at(7, "reserveBorrowLimit")
        bc_30d = val_at(30, "reserveBorrowLimit")
        with d2:
            st.metric("Borrow Cap", "" if pd.isna(curr_borrow_cap) else f"{float(curr_borrow_cap):,.0f}")
            render_delta_bubbles([
                ("1D", None if bc_1d is None else (float(curr_borrow_cap) - float(bc_1d))),
                ("7D", None if bc_7d is None else (float(curr_borrow_cap) - float(bc_7d))),
                ("30D", None if bc_30d is None else (float(curr_borrow_cap) - float(bc_30d))),
            ], percent=False)

        curr_borrow_util = None
        if pd.notnull(bor) and pd.notnull(curr_borrow_cap) and float(curr_borrow_cap) != 0:
            curr_borrow_util = float(bor) / float(curr_borrow_cap)
        bu_1d = val_at(1, "borrow_cap_util")
        bu_7d = val_at(7, "borrow_cap_util")
        bu_30d = val_at(30, "borrow_cap_util")
        with d3:
            st.metric("Borrow Cap Utilization", "-" if curr_borrow_util is None else f"{curr_borrow_util:.2%}")
            render_delta_bubbles([
                ("1D", None if bu_1d is None else (curr_borrow_util - bu_1d)),
                ("7D", None if bu_7d is None else (curr_borrow_util - bu_7d)),
                ("30D", None if bu_30d is None else (curr_borrow_util - bu_30d)),
            ], percent=True)

        rate = latest.iloc[0]["borrowInterestAPY"]
        r1 = val_at(1, "borrowInterestAPY")
        r7 = val_at(7, "borrowInterestAPY")
        r30 = val_at(30, "borrowInterestAPY")
        with d4:
            st.metric(
                "Borrow Rate %",
                "-" if pd.isna(rate) else f"{float(rate):.2%}",
                help=(
                    "Supply Interest APY: "
                    + (
                        f"{float(latest.iloc[0]['supplyInterestAPY']):.2%}" if pd.notna(latest.iloc[0]["supplyInterestAPY"]) else "-"
                    )
                ),
            )
            render_delta_bubbles([
                ("1D", None if r1 is None else (float(rate) - float(r1))),
                ("7D", None if r7 is None else (float(rate) - float(r7))),
                ("30D", None if r30 is None else (float(rate) - float(r30))),
            ], percent=True)

        st.divider()

        c_left, c_right = st.columns(2)
        with c_left:
            st.subheader("Supply & Borrow Over Time", help="Smoothed with 3-period rolling median")
            use_log_scale = st.toggle("Use log scale", value=True, key=f"log_toggle_{market_name}")
            sb = df[["timestamp", "totalSupply", "totalBorrows"]].copy().sort_values("timestamp")
            sb["sup_sm"] = pd.to_numeric(sb["totalSupply"], errors="coerce").rolling(window=3, min_periods=1).median()
            sb["bor_sm"] = pd.to_numeric(sb["totalBorrows"], errors="coerce").rolling(window=3, min_periods=1).median()
            fig_sb = go.Figure()
            fig_sb.add_trace(go.Scatter(x=sb["timestamp"], y=sb["sup_sm"], name="Total Supply", mode="lines", fill="tozeroy", line=dict(color="#1f77b4")))
            fig_sb.add_trace(go.Scatter(x=sb["timestamp"], y=sb["bor_sm"], name="Total Borrows", mode="lines", fill="tozeroy", line=dict(color="#ff7f0e")))
            fig_sb.update_layout(xaxis_title="Time", yaxis_title="Amount")
            if use_log_scale:
                fig_sb.update_yaxes(type="log")
            st.plotly_chart(fig_sb, use_container_width=True)

        with c_right:
            st.subheader("Cap Utilization Over Time", help="Smoothed with 3-period rolling median")
            cdf = df[["timestamp", "totalSupply", "totalBorrows", "reserveDepositLimit", "reserveBorrowLimit"]].copy().sort_values("timestamp")
            cdf["supply_cap_util"] = pd.to_numeric(cdf["totalSupply"], errors="coerce") / pd.to_numeric(cdf["reserveDepositLimit"], errors="coerce")
            cdf["borrow_cap_util"] = pd.to_numeric(cdf["totalBorrows"], errors="coerce") / pd.to_numeric(cdf["reserveBorrowLimit"], errors="coerce")
            cdf["supply_cap_util_sm"] = cdf["supply_cap_util"].rolling(window=3, min_periods=1).median()
            cdf["borrow_cap_util_sm"] = cdf["borrow_cap_util"].rolling(window=3, min_periods=1).median()
            fig_cu = go.Figure()
            fig_cu.add_trace(go.Scatter(x=cdf["timestamp"], y=cdf["supply_cap_util_sm"], name="Supply Cap Utilization", mode="lines"))
            fig_cu.add_trace(go.Scatter(x=cdf["timestamp"], y=cdf["borrow_cap_util_sm"], name="Borrow Cap Utilization", mode="lines"))
            fig_cu.update_layout(xaxis_title="Time", yaxis_title="Utilization")
            st.plotly_chart(fig_cu, use_container_width=True)

        st.divider()

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Utilization Over Time", help="Smoothed with 3-period rolling median")
            udf = df[["timestamp", "totalBorrows", "totalSupply"]].copy().sort_values("timestamp")
            udf["utilization"] = pd.to_numeric(udf["totalBorrows"], errors="coerce") / pd.to_numeric(udf["totalSupply"], errors="coerce")
            udf["util_sm"] = udf["utilization"].rolling(window=3, min_periods=1).median()
            fig_u = go.Figure()
            fig_u.add_trace(go.Scatter(x=udf["timestamp"], y=udf["util_sm"], name="Utilization", mode="lines"))
            fig_u.update_layout(xaxis_title="Time", yaxis_title="Utilization")
            st.plotly_chart(fig_u, use_container_width=True)

        with c4:
            st.subheader("Rates Over Time", help="Smoothed with 3-period rolling median")
            rdf = df[["timestamp", "borrowInterestAPY", "supplyInterestAPY"]].copy().sort_values("timestamp")
            rdf["borrow_sm"] = pd.to_numeric(rdf["borrowInterestAPY"], errors="coerce").rolling(window=3, min_periods=1).median() * 100.0
            rdf["supply_sm"] = pd.to_numeric(rdf["supplyInterestAPY"], errors="coerce").rolling(window=3, min_periods=1).median() * 100.0
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatter(x=rdf["timestamp"], y=rdf["borrow_sm"], name="Borrow APY %", mode="lines"))
            fig_r.add_trace(go.Scatter(x=rdf["timestamp"], y=rdf["supply_sm"], name="Supply APY %", mode="lines"))
            fig_r.update_layout(xaxis_title="Time", yaxis_title="Rate %")
            st.plotly_chart(fig_r, use_container_width=True)

        st.divider()

        st.subheader("IRM Changes Comparison", help="Shows the past 2 latest changes in the 30 days windows compared to the current IRM")
        curves = df[["timestamp", "borrowCurve"]].copy().sort_values("timestamp")
        def canon(x):
            if x is None:
                return None
            v = x
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except Exception:
                    return None
            elif not isinstance(v, (list, tuple, dict)):
                try:
                    if pd.isna(v):
                        return None
                except Exception:
                    return None
            try:
                return json.dumps(v, sort_keys=True)
            except Exception:
                return None
        curves["repr"] = curves["borrowCurve"].apply(canon)
        changes = []
        last = None
        for _, row in curves.iterrows():
            r = row["repr"]
            if r and r != last:
                changes.append({"timestamp": row["timestamp"], "repr": r, "curve": row["borrowCurve"]})
                last = r
        if changes:
            sel = changes[-3:]
            series = []
            opacities = [0.35, 0.65, 1.0]
            def fmt_ts(t):
                try:
                    tt = pd.to_datetime(t, utc=True, errors="coerce")
                    if pd.isna(tt):
                        return "-"
                    return tt.strftime("%Y-%m-%d %H:%M UTC")
                except Exception:
                    return str(t)
            for i, ch in enumerate(sel):
                lab = fmt_ts(ch["timestamp"])
                pts = ch["curve"]
                if isinstance(pts, str):
                    try:
                        pts = json.loads(pts)
                    except Exception:
                        pts = []
                for p in pts:
                    if isinstance(p, (list, tuple)) and len(p) == 2:
                        series.append({"util_pct": float(p[0]) * 100.0, "rate_pct": float(p[1]) * 100.0, "curve": lab})
            cdf = pd.DataFrame(series)
            fig_c = px.line(cdf, x="util_pct", y="rate_pct", color="curve", labels={"util_pct": "Utilization %", "rate_pct": "Borrow Rate %", "curve": ""}, color_discrete_sequence=["#1f77b4"])
            for j, tr in enumerate(fig_c.data):
                if j < len(opacities):
                    tr.opacity = opacities[j]
            st.plotly_chart(fig_c, use_container_width=True)
