import os
import re
from pathlib import Path

import streamlit as st
import pandas as pd

from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

PLAN_OUT_PATH = "landing_ytd_plan.parquet"
LY_OUT_PATH = "landing_ytd_vs_ly.parquet"

ALLOWED_SHEETS = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

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

def _detect_header_row(excel_path, sheet_name, max_scan_rows=25):
    preview_df = pd.read_excel(
        str(excel_path),
        sheet_name=sheet_name,
        header=None,
        nrows=int(max_scan_rows),
        engine=None
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
        header=int(header_row_idx)
    )
    df_val.columns = _clean_columns(df_val.columns)
    df_val = _drop_unnamed_and_empty_columns(df_val)
    return df_val

def _norm_col(col_name):
    return str(col_name).strip().lower().replace(" ", "_").replace("-", "_")

def _find_col(df_val, candidates):
    if df_val is None or len(df_val.columns) == 0:
        return None
    norm_map = {_norm_col(c): c for c in df_val.columns}
    for cand in candidates:
        cand_norm = _norm_col(cand)
        if cand_norm in norm_map:
            return norm_map[cand_norm]
    return None

def _canonical_location(loc_val):
    if pd.isna(loc_val):
        return None
    loc_str = str(loc_val).strip()
    if loc_str == "":
        return None
    loc_low = re.sub(r"\s+", " ", loc_str.lower()).strip()

    if loc_low == "grand total":
        return "Grand Total"

    if loc_low.endswith(" total"):
        base = loc_str[:-6].strip()
        base_low = base.lower()
        if base_low == "grand":
            return "Grand Total"
        return base

    return loc_str

def _build_landing_plan_df(workbook_path_obj):
    sheet_name = "YTD Plan vs Act"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name, max_scan_rows=35)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    div_col = _find_col(raw_df, ["Division", "Location"])
    if div_col is None:
        div_col = raw_df.columns[0]

    yards_prod_col = _find_col(raw_df, ["Yards Produced"])
    yards_plan_col = _find_col(raw_df, ["Yards Planned"])
    income_prod_col = _find_col(raw_df, ["Income Produced"])
    income_plan_col = _find_col(raw_df, ["Income Planned"])
    net_yards_inv_col = _find_col(raw_df, ["Net Yards Invoiced"])
    net_income_inv_col = _find_col(raw_df, ["Net Income Invoiced"])

    for col_name in [
        yards_prod_col,
        yards_plan_col,
        income_prod_col,
        income_plan_col,
        net_yards_inv_col,
        net_income_inv_col,
    ]:
        if col_name is not None and col_name in raw_df.columns:
            raw_df[col_name] = pd.to_numeric(raw_df[col_name], errors="coerce")

    div_series = raw_df[div_col].astype(str).str.strip()
    is_grand_total = div_series.str.lower().eq("grand total")
    is_div_total = div_series.str.lower().str.endswith(" total") & (~is_grand_total)

    keep_mask = is_grand_total | is_div_total
    df_keep = raw_df.loc[keep_mask, :].copy()

    df_keep["Location"] = df_keep[div_col].apply(_canonical_location)

    exclude_locs = {"design services", "design service"}
    df_keep = df_keep[~df_keep["Location"].astype(str).str.strip().str.lower().isin(exclude_locs)].copy()

    out_df = pd.DataFrame()
    out_df["Location"] = df_keep["Location"]

    out_df["Yards Produced"] = df_keep[yards_prod_col] if yards_prod_col in df_keep.columns else pd.NA
    out_df["Yards Planned"] = df_keep[yards_plan_col] if yards_plan_col in df_keep.columns else pd.NA
    out_df["Income Produced"] = df_keep[income_prod_col] if income_prod_col in df_keep.columns else pd.NA
    out_df["Income Planned"] = df_keep[income_plan_col] if income_plan_col in df_keep.columns else pd.NA
    out_df["Net Yards Invoiced"] = df_keep[net_yards_inv_col] if net_yards_inv_col in df_keep.columns else pd.NA
    out_df["Net Income Invoiced"] = df_keep[net_income_inv_col] if net_income_inv_col in df_keep.columns else pd.NA

    out_df = out_df.dropna(subset=["Location"])
    out_df["Location"] = out_df["Location"].astype(str).str.strip()

    def _loc_sort_key(x):
        x_low = str(x).strip().lower()
        if x_low == "grand total":
            return (9, x_low)
        return (0, x_low)

    out_df = out_df.sort_values(by="Location", key=lambda s: s.map(_loc_sort_key)).reset_index(drop=True)
    return out_df

def _build_landing_vs_ly_df(workbook_path_obj):
    sheet_name = "YTD vs LY"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name, max_scan_rows=35)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    div_col = _find_col(raw_df, ["Division", "Location"])
    if div_col is None:
        div_col = raw_df.columns[0]

    produced_cur_col = _find_col(raw_df, ["Produced Current", "Produced CY", "Produced", "Income Produced"])
    produced_ly_col = _find_col(raw_df, ["Produced LY", "Produced Prior", "Produced PY", "Income Produced LY"])
    invoiced_cur_col = _find_col(raw_df, ["Invoiced Current", "Invoiced CY", "Invoiced", "Net Income Invoiced"])
    invoiced_ly_col = _find_col(raw_df, ["Invoiced LY", "Invoiced Prior", "Invoiced PY", "Net Income Invoiced LY"])

    for col_name in [produced_cur_col, produced_ly_col, invoiced_cur_col, invoiced_ly_col]:
        if col_name is not None and col_name in raw_df.columns:
            raw_df[col_name] = pd.to_numeric(raw_df[col_name], errors="coerce")

    div_series = raw_df[div_col].astype(str).str.strip()
    is_grand_total = div_series.str.lower().eq("grand total")
    is_div_total = div_series.str.lower().str.endswith(" total") & (~is_grand_total)

    keep_mask = is_grand_total | is_div_total
    df_keep = raw_df.loc[keep_mask, :].copy()

    df_keep["Location"] = df_keep[div_col].apply(_canonical_location)

    exclude_locs = {"design services", "design service"}
    df_keep = df_keep[~df_keep["Location"].astype(str).str.strip().str.lower().isin(exclude_locs)].copy()

    out_df = pd.DataFrame()
    out_df["Location"] = df_keep["Location"]
    out_df["Produced Current"] = df_keep[produced_cur_col] if produced_cur_col in df_keep.columns else pd.NA
    out_df["Produced LY"] = df_keep[produced_ly_col] if produced_ly_col in df_keep.columns else pd.NA
    out_df["Invoiced Current"] = df_keep[invoiced_cur_col] if invoiced_cur_col in df_keep.columns else pd.NA
    out_df["Invoiced LY"] = df_keep[invoiced_ly_col] if invoiced_ly_col in df_keep.columns else pd.NA

    out_df = out_df.dropna(subset=["Location"])
    out_df["Location"] = out_df["Location"].astype(str).str.strip()

    def _loc_sort_key(x):
        x_low = str(x).strip().lower()
        if x_low == "grand total":
            return (9, x_low)
        return (0, x_low)

    out_df = out_df.sort_values(by="Location", key=lambda s: s.map(_loc_sort_key)).reset_index(drop=True)
    return out_df

def _write_landing_parquets(workbook_path_obj):
    plan_out = _build_landing_plan_df(workbook_path_obj)
    ly_out = _build_landing_vs_ly_df(workbook_path_obj)

    plan_out.to_parquet(PLAN_OUT_PATH, index=False)
    ly_out.to_parquet(LY_OUT_PATH, index=False)
    return plan_out, ly_out

with st.sidebar:
    st.header("Workbook")
    workbook_path = ensure_latest_workbook()
    st.write("Workbook path")
    st.code(str(workbook_path))

st.header("Landing data build")
st.caption("Writes: " + PLAN_OUT_PATH + " and " + LY_OUT_PATH)

c1, c2 = st.columns([1, 1])
with c1:
    build_clicked = st.button("Build Landing parquet files", type="primary")
with c2:
    clear_clicked = st.button("Clear cache")

if clear_clicked:
    st.cache_data.clear()
    st.success("Cache cleared.")
    st.rerun()

if build_clicked:
    with st.spinner("Building landing parquet files..."):
        plan_out_df, ly_out_df = _write_landing_parquets(workbook_path)

    st.cache_data.clear()
    st.success("Parquets written. Cache cleared.")

    st.subheader("Locations written")
    st.write(plan_out_df["Location"].tolist() if "Location" in plan_out_df.columns else [])
    st.write(ly_out_df["Location"].tolist() if "Location" in ly_out_df.columns else [])

    st.subheader("Plan parquet preview")
    st.dataframe(plan_out_df, use_container_width=True)

    st.subheader("Vs LY parquet preview")
    st.dataframe(ly_out_df, use_container_width=True)

    st.rerun()

st.divider()

st.header("Sheet preview")
sheet_name_choice = st.selectbox("Sheet", ALLOWED_SHEETS, index=0)

header_row = _detect_header_row(workbook_path, sheet_name_choice, max_scan_rows=35)
df_preview = _read_sheet_cached(str(workbook_path), sheet_name_choice, header_row)

st.caption("Detected header row index: " + str(header_row))
st.dataframe(df_preview.head(40), use_container_width=True)
