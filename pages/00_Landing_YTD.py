import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Landing - YTD", layout="wide")
st.title("Landing - YTD")
st.caption("YTD Scoreboard")

LY_OUT_PATH = "landing_ytd_vs_ly.parquet"

def _read_landing_df():
    df_val = pd.read_parquet(LY_OUT_PATH)
    if "Location" not in df_val.columns:
        df_val["Location"] = ""
    df_val["Location"] = df_val["Location"].astype(str).str.strip()

    num_cols = [
        "Written LY",
        "Written Current",
        "Produced LY",
        "Produced Current",
        "Invoiced LY",
        "Invoiced Current",
    ]
    for c in num_cols:
        if c in df_val.columns:
            df_val[c] = pd.to_numeric(df_val[c], errors="coerce")
        else:
            df_val[c] = np.

    return df_val

def _safe_loc_row(df_val, location_name):
    if df_val is None or df_val.empty:
        return pd.DataFrame(columns=df_val.columns if df_val is not None else ["Location"])
    out_df = df_val[df_val["Location"].str.lower() == str(location_name).strip().lower()].copy()
    return out_df

def _safe_scalar(loc_df, col_name, default_val=0.0):
    if loc_df is None or loc_df.empty:
        return float(default_val)
    if col_name not in loc_df.columns:
        return float(default_val)
    s_val = pd.to_numeric(loc_df[col_name], errors="coerce")
    if s_val.dropna().empty:
        return float(default_val)
    return float(s_val.dropna().iloc[0])

def _pct_vs_ly(curr_val, ly_val):
    curr_f = float(curr_val) if curr_val is not None else 0.0
    ly_f = float(ly_val) if ly_val is not None else 0.0
    if ly_f == 0.0:
        return None
    return (curr_f - ly_f) / ly_f

def _fmt_currency(x_val):
    try:
        x_f = float(x_val)
    except Exception:
        x_f = 0.0
    return "${:,.0f}".format(x_f)

def _fmt_pct(p_val):
    if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)):
        return "—"
    return "{:.1f}% vs LY".format(100.0 * float(p_val))

def _delta_color(p_val):
    if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)):
        return "#6b7280"
    if float(p_val) >= 0:
        return "#16a34a"
    return "#dc2626"

def _metric_block(title_txt, curr_val, ly_val):
    pct_val = _pct_vs_ly(curr_val, ly_val)
    color_val = _delta_color(pct_val)

    st.markdown(
        """
        <div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 16px; background: white;">
          <div style="font-size: 14px; color: #374151; margin-bottom: 6px; font-weight: 600;">{title}</div>
          <div style="font-size: 34px; line-height: 1.1; font-weight: 700; color: #111827;">{curr}</div>
          <div style="margin-top: 6px; display: inline-block; padding: 4px 10px; border-radius: 999px; background: #f3f4f6; color: {color}; font-weight: 600; font-size: 13px;">
            {pct}
          </div>
        </div>
        """.replace("{title}", str(title_txt))
           .replace("{curr}", _fmt_currency(curr_val))
           .replace("{pct}", _fmt_pct(pct_val))
           .replace("{color}", str(color_val)),
        unsafe_allow_html=True,
    )

def _render_location(df_val, loc_name, header_label=None):
    label = loc_name if header_label is None else header_label
    st.subheader(str(label))

    loc_df = _safe_loc_row(df_val, loc_name)

    written_curr = _safe_scalar(loc_df, "Written Current", default_val=0.0)
    written_ly = _safe_scalar(loc_df, "Written LY", default_val=0.0)
    produced_curr = _safe_scalar(loc_df, "Produced Current", default_val=0.0)
    produced_ly = _safe_scalar(loc_df, "Produced LY", default_val=0.0)
    invoiced_curr = _safe_scalar(loc_df, "Invoiced Current", default_val=0.0)
    invoiced_ly = _safe_scalar(loc_df, "Invoiced LY", default_val=0.0)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        _metric_block("Written - Income", written_curr, written_ly)
    with col_b:
        _metric_block("Produced - Income", produced_curr, produced_ly)
    with col_c:
        _metric_block("Invoiced - Net Income", invoiced_curr, invoiced_ly)

    with st.expander("Details"):
        st.dataframe(loc_df, width="stretch")

try:
    landing_df = _read_landing_df()
except Exception as e:
    st.error("Could not load " + LY_OUT_PATH)
    st.code(str(e))
    st.stop()

st.markdown("### Divisions")

_render_location(landing_df, "Digital")
st.divider()
_render_location(landing_df, "Screen Print")
st.divider()
_render_location(landing_df, "Grand Total", header_label="Grand Total")
