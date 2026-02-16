import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Landing - YTD", layout="wide")

@st.cache_data
def load_landing_parquets():
    plan_df = pd.read_parquet("landing_ytd_plan.parquet")
    ly_df = pd.read_parquet("landing_ytd_vs_ly.parquet")
    return plan_df, ly_df

def fmt_int(x):
    if pd.isna(x):
        return "-"
    return "{:,.0f}".format(float(x))

def fmt_money(x):
    if pd.isna(x):
        return "-"
    return "${:,.0f}".format(float(x))

def fmt_pct(x):
    if pd.isna(x):
        return "-"
    return "{:.1%}".format(float(x))

def get_row(df, location_name):
    sub = df[df["Location"] == location_name]
    if len(sub) == 0:
        return None
    return sub.iloc[0]

plan_df, ly_df = load_landing_parquets()

st.title("YTD Scoreboard")

st.caption("Landing is YTD-first: plan attainment + vs last year. Totals/subtotals removed; Grand Totals preserved.")

locations_order = ["Brooklyn", "Passaic"]
location_labels = {
    "Brooklyn": "Digital (Brooklyn)",
    "Passaic": "Screen Print (Passaic)"
}

for loc in locations_order:
    st.subheader(location_labels.get(loc, loc))

    plan_row = get_row(plan_df, loc)
    ly_rows = ly_df[ly_df["Location"] == loc]
    ly_row = ly_rows.iloc[0] if len(ly_rows) > 0 else None

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### Written (vs LY)")
        if ly_row is None:
            st.metric("YTD Income Written", "-")
        else:
            st.metric(
                "YTD Income Written",
                fmt_money(ly_row.get("YTD_Income_Written")),
                fmt_money(ly_row.get("Delta_Income_Written"))
            )
            st.write("vs LY " + fmt_pct(ly_row.get("Pct_Income_Written")))

    with c2:
        st.markdown("#### Produced (vs Plan + vs LY)")
        if plan_row is None:
            st.metric("YTD Yards Produced", "-")
        else:
            st.metric(
                "YTD Yards Produced",
                fmt_int(plan_row.get("Yards Produced")),
                fmt_int(plan_row.get("Yards Produced vs Plan"))
            )
            st.write("Plan attainment " + fmt_pct(plan_row.get("% Produced vs Plan")))

        if ly_row is not None:
            st.write("YTD Income Produced " + fmt_money(ly_row.get("YTD_Income_Produced")))
            st.write("vs LY " + fmt_money(ly_row.get("Delta_Income_Produced")) + " (" + fmt_pct(ly_row.get("Pct_Income_Produced")) + ")")

    with c3:
        st.markdown("#### Invoiced (vs Plan + vs LY)")
        if plan_row is None:
            st.metric("YTD Net Yards Invoiced", "-")
        else:
            st.metric(
                "YTD Net Yards Invoiced",
                fmt_int(plan_row.get("Net Yards Invoiced"))
            )
            st.write("YTD Net Income Invoiced " + fmt_money(plan_row.get("Net Income Invoiced")))

        if ly_row is not None:
            st.write("YTD Net Income Invoiced (LY compare) " + fmt_money(ly_row.get("YTD_Net_Income_Invoiced")))
            st.write("vs LY " + fmt_money(ly_row.get("Delta_Net_Income_Invoiced")) + " (" + fmt_pct(ly_row.get("Pct_Net_Income_Invoiced")) + ")")

    st.divider()

st.markdown("#### Optional: Grand Total")
gt_plan = plan_df[plan_df["Division"] == "Grand Total"]
gt_ly = ly_df[ly_df["Division"] == "Grand Total"]

gtp = gt_plan.iloc[0] if len(gt_plan) else None
gtl = gt_ly.iloc[0] if len(gt_ly) else None

g1, g2, g3 = st.columns(3)
with g1:
    st.metric("YTD Yards Produced (GT)", fmt_int(gtp.get("Yards Produced")) if gtp is not None else "-")
with g2:
    st.metric("YTD vs Plan (GT)", fmt_int(gtp.get("Yards Produced vs Plan")) if gtp is not None else "-")
with g3:
    st.metric("YTD Income Written vs LY (GT)", fmt_money(gtl.get("Delta_Income_Written")) if gtl is not None else "-")
