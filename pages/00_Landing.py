import streamlit as st
import pandas as pd

from app_tables import require_tables, get_table, list_tables, tables_debug_map

st.set_page_config(page_title="Landing", layout="wide")
st.title("Landing")

tables = require_tables()

focus_sheets = [
    "Written produced by week",
    "Written produced invoiced",
    "YTD plan v Actual",
    "YTD v LY",
    "Color yds",
    "WIP",
    "Yds wasted",
]

st.caption("Focused mode: showing only the 7 priority sheets for now.")

st.subheader("Sheet availability")

avail_rows = []
for s in focus_sheets:
    df_tmp, actual_name = get_table(tables, s)
    avail_rows.append(
        {
            "Requested": s,
            "Found": "YES" if df_tmp is not None else "NO",
            "Actual sheet name": "" if actual_name is None else actual_name,
            "Rows": "" if df_tmp is None else len(df_tmp),
            "Cols": "" if df_tmp is None else len(df_tmp.columns),
        }
    )

avail_df = pd.DataFrame(avail_rows)
st.dataframe(avail_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Quick previews (head only)")

col_left, col_right = st.columns(2)
for idx, s in enumerate(focus_sheets):
    df_tmp, actual_name = get_table(tables, s)

    target_col = col_left if idx % 2 == 0 else col_right
    with target_col:
        st.markdown("**" + s + "**")
        if df_tmp is None:
            st.error("Missing")
        else:
            st.caption("Loaded as: " + str(actual_name))
            st.dataframe(df_tmp.head(8), use_container_width=True)

st.divider()

tab_previews, tab_debug = st.tabs(["Inspect a sheet", "Debug"])

with tab_previews:
    st.subheader("Pick a sheet to inspect")

    picked = st.selectbox("Sheet", focus_sheets, index=0)
    df_picked, actual_name = get_table(tables, picked)

    if df_picked is None:
        st.error("Missing: " + picked)
    else:
        st.caption("Loaded as: " + str(actual_name))
        st.dataframe(df_picked.head(50), use_container_width=True)

        num_cols = []
        for c in df_picked.columns:
            series_num = pd.to_numeric(df_picked[c], errors="coerce")
            if series_num.notna().sum() >= max(5, int(0.2 * len(series_num))):
                num_cols.append(c)

        if len(num_cols) > 0:
            st.subheader("Quick chart (first numeric column)")
            col0 = num_cols[0]
            chart_df = pd.DataFrame(
                {
                    "row": list(range(min(120, len(df_picked)))),
                    col0: pd.to_numeric(df_picked[col0], errors="coerce").head(120),
                }
            )
            chart_df = chart_df.dropna()
            if len(chart_df) > 0:
                st.line_chart(chart_df.set_index("row")[col0], use_container_width=True)
            else:
                st.info("No numeric values to chart in first 120 rows.")
        else:
            st.info("No obvious numeric columns detected yet.")

with tab_debug:
    st.subheader("Loaded sheet names (from session state)")
    st.write(list_tables(tables))

    st.subheader("Normalized sheet names (helps debug matching)")
    st.dataframe(pd.DataFrame(tables_debug_map(tables)), use_container_width=True, hide_index=True)
