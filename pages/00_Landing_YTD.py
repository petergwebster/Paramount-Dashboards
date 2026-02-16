import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Landing - YTD", layout="wide")
st.title("YTD Scoreboard")

LY_OUT_PATH = "landing_ytd_vs_ly.parquet"

def read_landing_df():
    df_val = pd.read_parquet(LY_OUT_PATH)

    if "Location" not in df_val.columns:
        df_val["Location"] = ""

    df_val["Location"] = df_val["Location"].astype(str).str.strip()

    metric_cols = [
        "Written LY",
        "Written Current",
        "Produced LY",
        "Produced Current",
        "Invoiced LY",
        "Invoiced Current",
    ]

    for col_name in metric_cols:
        if col_name in df_val.columns:
            df_val[col_name] = pd.to_numeric(df_val[col_name], errors="coerce")
        else:
            df_val[col_name] = None

    return df_val

def safe_scalar(loc_df, col_name, default_val=0.0):
    if loc_df is None or loc_df.empty:
        return float(default_val)
    if col_name not in loc_df.columns:
        return float(default_val)

    s_val = pd.to_numeric(loc_df[col_name], errors="coerce")
    if s_val.dropna().empty:
        return float(default_val)

    return float(s_val.dropna().iloc[0])

def pct_vs_ly(curr_val, ly_val):
    curr_f = float(curr_val) if curr_val is not None else 0.0
    ly_f = float(ly_val) if ly_val is not None else 0.0
    if ly_f == 0.0:
        return None
    return (curr_f - ly_f) / ly_f

def fmt_currency(x_val):
    try:
        x_f = float(x_val)
    except Exception:
        x_f = 0.0
    return "${:,.0f}".format(x_f)

def fmt_pct(p_val):
    if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)):
        return "—"
    return "{:.1f}% vs LY".format(100.0 * float(p_val))

def delta_color(p_val):
    if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)):
        return "#6b7280"
    if float(p_val) >= 0:
        return "#16a34a"
    return "#dc2626"

def metric_card(title_txt, curr_val, ly_val):
    pct_val = pct_vs_ly(curr_val, ly_val)
    color_val = delta_color(pct_val)

    html_val = """
    <div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 16px; background: white;">
      <div style="font-size: 14px; color: #374151; margin-bottom: 6px; font-weight: 600;">TITLE</div>
      <div style="font-size: 34px; line-height: 1.1; font-weight: 700; color: #111827;">CURR</div>
      <div style="margin-top: 6px; display: inline-block; padding: 4px 10px; border-radius: 999px; background: #f3f4f6; color: COLOR; font-weight: 600; font-size: 13px;">
        PCT
      </div>
    </div>
    """
    html_val = html_val.replace("TITLE", str(title_txt))
    html_val = html_val.replace("CURR", fmt_currency(curr_val))
    html_val = html_val.replace("PCT", fmt_pct(pct_val))
    html_val = html_val.replace("COLOR", str(color_val))
    st.markdown(html_val, unsafe_allow_html=True)

def render_location(landing_df, location_name, header_label=None):
    label = location_name if header_label is None else header_label
    st.subheader(str(label))

    loc_df = landing_df[landing_df["Location"].str.lower() == str(location_name).strip().lower()].copy()

    written_curr = safe_scalar(loc_df, "Written Current", default_val=0.0)
    written_ly = safe_scalar(loc_df, "Written LY", default_val=0.0)
    produced_curr = safe_scalar(loc_df, "Produced Current", default_val=0.0)
    produced_ly = safe_scalar(loc_df, "Produced LY", default_val=0.0)
    invoiced_curr = safe_scalar(loc_df, "Invoiced Current", default_val=0.0)
    invoiced_ly = safe_scalar(loc_df, "Invoiced LY", default_val=0.0)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        metric_card("Written - Income", written_curr, written_ly)
    with col_b:
        metric_card("Produced - Income", produced_curr, produced_ly)
    with col_c:
        metric_card("Invoiced - Net Income", invoiced_curr, invoiced_ly)

    with st.expander("Details"):
        st.dataframe(loc_df, width="stretch")

landing_df = read_landing_df()

render_location(landing_df, "Digital")
st.divider()
render_location(landing_df, "Screen Print")
st.divider()
render_location(landing_df, "Grand Total", header_label="Grand Total")
