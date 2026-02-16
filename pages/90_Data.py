from pathlib import Path
import re
import streamlit as st
import pandas as pd

from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Admin - Data")

PLAN_OUT_PATH = "landing_ytd_plan.parquet"
LY_OUT_PATH = "landing_ytd_vs_ly.parquet"
TREND_OUT_PATH = "trend_weekly.parquet"
WIP_OUT_PATH = "wip.parquet"
COLOR_YARDS_OUT_PATH = "color_yards.parquet"
YARDS_WASTED_OUT_PATH = "yards_wasted.parquet"

EXCLUDE_DIVISIONS = {
    "design services",
    "design services total",
}

def _clean_columns(cols_val):
    clean_cols = []
    for c in cols_val:
        c_str = str(c)
        c_str = re.sub(r"\s+", " ", c_str).strip()
        clean_cols.append(c_str)
    return clean_cols

def _drop_unnamed_and_empty_columns(df_val):
    cols_str = df_val.columns.astype(str)
    keep_mask = ~cols_str.str.match(r"^Unnamed")
    df_val = df_val.loc[:, keep_mask]
    df_val = df_val.dropna(axis=1, how="all")
    return df_val

def _score_header_row(row_vals):
    vals = ["" if pd.isna(x) else str(x).strip() for x in row_vals]
    non_empty = [v for v in vals if v != ""]
    if len(non_empty) == 0:
        return 0
    unique_count = len(set(non_empty))
    score = len(non_empty) + unique_count
    return score

def _detect_header_row(excel_path, sheet_name, max_scan_rows=30):
    preview_df = pd.read_excel(
        str(excel_path),
        sheet_name=sheet_name,
        header=None,
        nrows=int(max_scan_rows),
    )
    best_idx = 0
    best_score = -1
    for idx_val in range(preview_df.shape[0]):
        score_val = _score_header_row(preview_df.iloc[idx_val].tolist())
        if score_val > best_score:
            best_score = score_val
            best_idx = idx_val
    return int(best_idx)

@st.cache_data(show_spinner=False)
def _read_sheet_cached(excel_path_str, sheet_name, header_row_idx):
    df_val = pd.read_excel(
        excel_path_str,
        sheet_name=sheet_name,
        header=int(header_row_idx),
    )
    df_val.columns = _clean_columns(df_val.columns)
    df_val = _drop_unnamed_and_empty_columns(df_val)
    return df_val

def _make_parquet_safe(df_val):
    if df_val is None:
        return df_val

    out_df = df_val.copy()

    for col_val in out_df.columns:
        if out_df[col_val].dtype == "object":
            non_null = out_df[col_val].dropna()
            if len(non_null) == 0:
                continue
            sample = non_null.iloc[0]
            if isinstance(sample, (list, dict)):
                out_df[col_val] = out_df[col_val].astype(str)

    return out_df

def _write_parquet_safe(df_val, out_path):
    safe_df = _make_parquet_safe(df_val)
    safe_df.to_parquet(out_path, index=False)
    return safe_df

def _clean_loc(loc_val):
    if pd.isna(loc_val):
        return None
    s_val = str(loc_val).strip()
    if s_val == "":
        return None
    s_val = re.sub(r"\s+", " ", s_val)
    return s_val

def _is_total_row(loc_val):
    if pd.isna(loc_val):
        return False
    s_val = str(loc_val).strip().lower()
    return (s_val == "grand total") or s_val.endswith(" total")

def _base_division_name(loc_val):
    if pd.isna(loc_val):
        return None
    s_val = re.sub(r"\s+", " ", str(loc_val).strip())
    s_low = s_val.lower()
    if s_low == "grand total":
        return "Grand Total"
    if s_low.endswith(" total"):
        return s_val[:-6].strip()
    return s_val

def _build_landing_vs_ly_df(workbook_path_obj):
    sheet_name = "YTD vs LY"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    df_val = raw_df.copy()
    df_val = df_val.dropna(axis=0, how="all")

    exclude_set = set([x.lower() for x in EXCLUDE_DIVISIONS])

    def _block(df_in, div_col, ly_col, ty_col, out_ly_name, out_ty_name):
        keep_cols = [div_col, ly_col, ty_col]
        keep_cols = [c for c in keep_cols if c in df_in.columns]
        slim = df_in[keep_cols].copy()

        slim["Location"] = slim[div_col].apply(_base_division_name).apply(_clean_loc)
        slim = slim[slim[div_col].apply(_is_total_row)].copy()
        slim = slim.dropna(subset=["Location"]).copy()
        slim = slim[~slim["Location"].astype(str).str.strip().str.lower().isin(exclude_set)].copy()

        slim[out_ly_name] = pd.to_numeric(slim[ly_col], errors="coerce")
        slim[out_ty_name] = pd.to_numeric(slim[ty_col], errors="coerce")

        return slim[["Location", out_ly_name, out_ty_name]].copy()

    written_df = _block(
        df_val,
        "Divisions",
        "2024 Income Written",
        "2025 Income Written",
        "Written LY",
        "Written Current",
    )

    produced_div_col = "Divisions.1" if "Divisions.1" in df_val.columns else "Divisions"
    produced_df = _block(
        df_val,
        produced_div_col,
        "2024 Income Produced",
        "2025 Income Produced",
        "Produced LY",
        "Produced Current",
    )

    invoiced_div_col = "Divisions.2" if "Divisions.2" in df_val.columns else "Divisions"
    invoiced_df = _block(
        df_val,
        invoiced_div_col,
        "2024 Net Income Invoiced",
        "2025 Net Income Invoiced",
        "Invoiced LY",
        "Invoiced Current",
    )

    out_df = written_df.merge(produced_df, on="Location", how="outer").merge(invoiced_df, on="Location", how="outer")
    out_df = out_df.dropna(subset=["Location"]).copy()

    out_df["__sort"] = out_df["Location"].astype(str).str.strip().str.lower().apply(
        lambda x: 9999 if x == "grand total" else 0
    )
    out_df = out_df.sort_values(["__sort", "Location"]).drop(columns=["__sort"]).reset_index(drop=True)

    return out_df

def _build_landing_plan_df(workbook_path_obj):
    sheet_name = "YTD Plan vs Act"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)
    df_val = raw_df.copy().dropna(axis=0, how="all")
    return df_val.reset_index(drop=True)

def _build_trend_weekly_df(workbook_path_obj):
    sheet_name = "Written and Produced by Week"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)
    df_val = raw_df.copy().dropna(axis=0, how="all")
    return df_val.reset_index(drop=True)

def _build_wip_df(workbook_path_obj):
    sheet_name = "WIP"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)
    df_val = raw_df.copy().dropna(axis=0, how="all")
    return df_val.reset_index(drop=True)

def _build_color_yards_df(workbook_path_obj):
    sheet_name = "Color Yards"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)
    df_val = raw_df.copy().dropna(axis=0, how="all")
    return df_val.reset_index(drop=True)

def _build_yards_wasted_df(workbook_path_obj):
    sheet_name = "Yards Wasted"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)
    df_val = raw_df.copy().dropna(axis=0, how="all")
    return df_val.reset_index(drop=True)

def _write_all_parquets(workbook_path_obj):
    plan_df_val = _build_landing_plan_df(workbook_path_obj)
    ly_df_val = _build_landing_vs_ly_df(workbook_path_obj)
    trend_df_val = _build_trend_weekly_df(workbook_path_obj)
    wip_df_val = _build_wip_df(workbook_path_obj)
    color_df_val = _build_color_yards_df(workbook_path_obj)
    wasted_df_val = _build_yards_wasted_df(workbook_path_obj)

    plan_df_val = _write_parquet_safe(plan_df_val, PLAN_OUT_PATH)
    ly_df_val = _write_parquet_safe(ly_df_val, LY_OUT_PATH)
    trend_df_val = _write_parquet_safe(trend_df_val, TREND_OUT_PATH)
    wip_df_val = _write_parquet_safe(wip_df_val, WIP_OUT_PATH)
    color_df_val = _write_parquet_safe(color_df_val, COLOR_YARDS_OUT_PATH)
    wasted_df_val = _write_parquet_safe(wasted_df_val, YARDS_WASTED_OUT_PATH)

    return plan_df_val, ly_df_val, trend_df_val, wip_df_val, color_df_val, wasted_df_val

st.markdown("#### Workbook")
with st.spinner("Checking workbook..."):
    workbook_path_str = ensure_latest_workbook()
workbook_path_obj = Path(workbook_path_str)

st.write("Using workbook")
st.code(str(workbook_path_obj))

if not workbook_path_obj.exists():
    st.error("Workbook not found at " + str(workbook_path_obj))
    st.stop()

st.markdown("#### Parquet build")
st.write("Click to generate all parquet files used by the dashboard pages.")
build_clicked = st.button("Build parquets", type="primary")

if build_clicked:
    with st.spinner("Building parquets..."):
        plan_df, ly_df, trend_df, wip_df, color_df, wasted_df = _write_all_parquets(workbook_path_obj)

    st.success("Parquets written successfully.")

    st.markdown("#### Outputs preview")
    st.write(PLAN_OUT_PATH)
    st.dataframe(plan_df, width="stretch")

    st.write(LY_OUT_PATH)
    st.dataframe(ly_df, width="stretch")

    st.write(TREND_OUT_PATH)
    st.dataframe(trend_df.head(30), width="stretch")

    st.write(WIP_OUT_PATH)
    st.dataframe(wip_df.head(30), width="stretch")

    st.write(COLOR_YARDS_OUT_PATH)
    st.dataframe(color_df.head(30), width="stretch")

    st.write(YARDS_WASTED_OUT_PATH)
    st.dataframe(wasted_df.head(30), width="stretch")
