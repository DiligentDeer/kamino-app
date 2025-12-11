import pandas as pd
import streamlit as st

def fmt_compact(n: float) -> str:
    """
    Format a number with compact suffixes (K, M, B, T).
    Returns "-" if n is None or NaN.
    """
    if n is None or pd.isna(n):
        return "-"
    try:
        n_float = float(n)
    except (ValueError, TypeError):
        return "-"
        
    sign = -1 if n_float < 0 else 1
    v = abs(n_float)
    units = [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]
    for thresh, u in units:
        if v >= thresh:
            return ("-" if sign < 0 else "") + f"{v/thresh:.1f}{u}"
    return ("-" if sign < 0 else "") + f"{v:,.0f}"

def render_delta_bubbles(items: list, percent: bool = False):
    """
    Render a series of bubbles showing delta changes.
    
    Args:
        items: List of tuples (label, delta_value)
        percent: If True, format delta as percentage.
    """
    def style(delta):
        if delta is None:
            return ("#f1f3f5", "#555", "")
        # Use a small epsilon for float comparison if needed, but simple > 0 works for now
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        bg = "#e6f4ea" if delta > 0 else ("#fde8e8" if delta < 0 else "#f1f3f5")
        fg = "#0a0" if delta > 0 else ("#d00" if delta < 0 else "#555")
        return (bg, fg, arrow)

    def fmt(delta):
        if delta is None:
            return "-"
        return (fmt_compact(delta) if not percent else f"{delta:.2%}")

    pills = []
    for lbl, delta in items:
        bg, fg, arrow = style(delta)
        value_txt = fmt(delta)
        # Using a span with inline styles to create the pill/bubble effect
        pills.append(
            f"<span style='display:inline-block;margin-right:6px;margin-top:2px;padding:4px 8px;"
            f"border-radius:999px;background:{bg};color:{fg};font-weight:500;font-size:12px;line-height:1;'>"
            f"<strong>{lbl}</strong> "
            f"{'-' if delta is None else f'{arrow} {value_txt}'}"
            f"</span>"
        )
    
    st.markdown("".join(pills), unsafe_allow_html=True)
