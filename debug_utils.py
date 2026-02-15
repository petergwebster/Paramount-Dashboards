import pandas as pd
import streamlit as st

def _coerce_num(series_in):
    series_as_str = series_in.astype(str)
    series_as_str = series_as_str.str.replace(",", "", regex=False)
    series_as_str = series_as_str.str.replace("(", "-", regex=False).str.replace(")", "", regex=False)
    return pd.to_numeric(series_as_str, errors="coerce")

def numeric_strength_table(df_in, top_n=20):
    if df_in is None or len(df_in.columns) == 0:
        return pd.DataFrame()

    rows = []
    for c in df_in.columns:
        num_non_null = int(_coerce_num(df_in[c]).notna().sum())
        rows.append({"col": c, "non_null_numeric": num_non_null})

    out_df = pd.DataFrame(rows).sort_values("non_null_numeric", ascending=False).head(top_n)
    return out_df

def value_counts_table(df_in, col_name, top_n=25):
    if df_in is None or col_name is None or col_name not in df_in.columns:
        return None

    vc = (
        df_in[col_name]
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
        .str.lower()
        .value_counts(dropna=False)
        .head(top_n)
    )
    return vc

def render_debug_tab(
    *,
    title="Debug",
    meta_dict=None,
    df_clean=None,
    df_raw=None,
    time_col=None,
    measure_cols=None,
    show_numeric_strength=True,
):
    st.subheader(title)

    if meta_dict is not None:
        st.markdown("#### Chosen columns / metadata")
        st.write(meta_dict)

    if time_col is not None and df_clean is not None and time_col in df_clean.columns:
        st.markdown("#### Time bucket value counts")
        vc = value_counts_table(df_clean, time_col, top_n=25)
        if vc is not None:
            st.write(vc)

    if measure_cols is None:
        measure_cols = []

    for c in measure_cols:
        if df_clean is not None and c in df_clean.columns:
            st.markdown("#### Measure column value counts (top 20 non-null) for `" + str(c) + "`")
            s = df_clean[c]
            s_num = _coerce_num(s)
            s_num = s_num[s_num.notna()]
            if len(s_num) == 0:
                st.write(s.astype(str).value_counts(dropna=False).head(20))
            else:
                st.write(s_num.value_counts().head(20))

    if show_numeric_strength and df_clean is not None:
        st.markdown("#### Numeric strength (top columns by numeric non-nulls)")
        st.dataframe(numeric_strength_table(df_clean, top_n=20), use_container_width=True)

    if df_clean is not None:
        st.markdown("#### All columns (cleaned)")
        st.write(list(df_clean.columns))

    if df_raw is not None:
        st.markdown("#### Raw head (before header promotion)")
        st.dataframe(df_raw.head(10), use_container_width=True)

    if df_clean is not None:
        st.markdown("#### Clean head (after header promotion + dedupe)")
        st.dataframe(df_clean.head(60), use_container_width=True)
