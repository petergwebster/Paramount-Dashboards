import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cockpit", layout="wide")

st.markdown("## Cockpit")
st.markdown("This page reads tables from `st.session_state['tables']` (no disk reload).")

tables = st.session_state.get("tables")

if tables is None:
    st.warning("No data loaded yet. Go to the Data page and click Load workbook.")
    st.stop()

if not isinstance(tables, dict) or len(tables) == 0:
    st.warning("Tables are empty. Go to the Data page and click Load workbook again.")
    st.stop()

table_keys = sorted(list(tables.keys()))

st.markdown("### Tables available (from memory)")
st.write("Total tables")
st.write(len(table_keys))

with st.sidebar:
    st.header("Cockpit Controls")
    selected_key = st.selectbox("Choose table", options=table_keys, index=0)

df = tables[selected_key]

st.markdown("### Selected table")
st.write("Key")
st.write(selected_key)

st.write("Shape")
st.write([int(df.shape[0]), int(df.shape[1])])

st.markdown("#### Preview")
st.dataframe(df.head(50), use_container_width=True)

st.markdown("#### Quick KPI: non-empty cells (rough completeness)")
non_null_total = int(df.notna().sum().sum())
total_cells = int(df.shape[0] * df.shape[1])
pct_filled = 0.0
if total_cells > 0:
    pct_filled = non_null_total / total_cells

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Rows", int(df.shape[0]))
with col_b:
    st.metric("Cols", int(df.shape[1]))
with col_c:
    st.metric("Filled cells percent", str(round(pct_filled * 100.0, 1)) + "%")

st.markdown("### Try to auto-plot by date (if a date-like column exists)")
date_col = None
for c in list(df.columns):
    c_str = str(c).strip().lower()
    if "date" in c_str or "week" in c_str or "month" in c_str:
        date_col = c
        break

if date_col is None:
    st.info("No obvious date/week/month column detected yet. Once we identify the real time column, we’ll plot the actual KPI trend.")
else:
    df_plot = df.copy()

    df_plot[date_col] = pd.to_datetime(df_plot[date_col], errors="coerce")
    df_plot = df_plot[df_plot[date_col].notna()].copy()

    if df_plot.shape[0] == 0:
        st.info("Found a date-like column but none of its values parsed as dates.")
    else:
        df_plot = df_plot.sort_values(date_col)

        value_col = None
        for c in list(df_plot.columns):
            if c == date_col:
                continue
            c_str = str(c).strip().lower()
            if "total" in c_str or "count" in c_str or "written" in c_str or "sales" in c_str:
                value_col = c
                break

        if value_col is None:
            st.info("Date column detected, but no obvious numeric KPI column found. Next step is to pick the KPI column explicitly.")
        else:
            df_plot[value_col] = pd.to_numeric(df_plot[value_col], errors="coerce")
            df_plot = df_plot[df_plot[value_col].notna()].copy()

            if df_plot.shape[0] == 0:
                st.info("Value column detected, but values are not numeric after coercion.")
            else:
                st.line_chart(df_plot.set_index(date_col)[value_col])
