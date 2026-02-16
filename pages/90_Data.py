from pathlib import Path
import datetime as dt
import re
import os
import streamlit as st
import pandas as pd

from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Data")

ALLOWED_SHEETS = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

PLAN_OUT_PATH = "landing_ytd_plan.parquet"
LY_OUT_PATH = "landing_ytd_vs_ly.parquet"


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
        row_vals = preview_df.iloc[idx_val].tolist()
        score_val = _score_header_row(row_vals)
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


def _coerce_numeric(df_val, col_name):
    if df_val is None or col_name is None:
        return df_val
    if col_name not in df_val.columns:
        return df_val
    df_val[col_name] = pd.to_numeric(df_val[col_name], errors="coerce")
    return df_val


def _canonical_location(loc_val):
    if pd.isna(loc_val):
        return None
    loc_str = str(loc_val).strip()
    if loc_str == "":
        return None

    loc_low = re.sub(r"\s+", " ", loc_str.lower()).strip()

    if "brooklyn" in loc_low:
        return "Brooklyn"
    if "passaic" in loc_low:
        return "Passaic"
    if ("grand" in loc_low and "total" in loc_low) or loc_low in ["grandtotal", "total", "overall", "company total", "all"]:
        return "Grand Total"

    return loc_str


def _build_landing_plan_df(workbook_path_obj):
    sheet_name = "YTD Plan vs Act"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name, max_scan_rows=25)
    df_val = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    loc_col = _find_col(df_val, ["Location"])
    if loc_col is None:
        df_val = df_val.rename(columns={df_val.columns[0]: "Location"})
        loc_col = "Location"

    rename_map = {}

    candidates_to_dst = [
        (["Yards Produced", "Produced Yards", "Yards Prod", "Prod Yards"], "Yards Produced"),
        (["Yards Planned", "Planned Yards", "Yards Plan", "Plan Yards"], "Yards Planned"),
        (["Income Produced", "Produced Income", "Income Prod", "Produced $"], "Income Produced"),
        (["Income Planned", "Planned Income", "Income Plan", "Plan $"], "Income Planned"),
        (["Net Yards Invoiced", "Invoiced Net Yards", "Net Yds Invoiced"], "Net Yards Invoiced"),
        (["Net Income Invoiced", "Invoiced Net Income", "Net $ Invoiced"], "Net Income Invoiced"),
    ]

    for src_list, dst in candidates_to_dst:
        found = _find_col(df_val, src_list)
        if found is not None:
            rename_map[found] = dst

    df_val = df_val.rename(columns=rename_map)

    df_val["Location"] = df_val[loc_col].apply(_canonical_location)
    df_val = df_val.dropna(subset=["Location"])

    numeric_cols = [
        "Yards Produced",
        "Yards Planned",
        "Income Produced",
        "Income Planned",
        "Net Yards Invoiced",
        "Net Income Invoiced",
    ]
    for col_val in numeric_cols:
        df_val = _coerce_numeric(df_val, col_val)

    keep_cols = ["Location"] + [c for c in numeric_cols if c in df_val.columns]
    df_out = df_val[keep_cols].copy()

    df_out["Location"] = df_out["Location"].astype(str).str.strip()
    df_out = df_out[df_out["Location"].str.len() > 0]

    return df_out


def _build_landing_ly_df(workbook_path_obj):
    sheet_name = "YTD vs LY"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name, max_scan_rows=25)
    df_val = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    loc_col = _find_col(df_val, ["Location"])
    if loc_col is None:
        df_val = df_val.rename(columns={df_val.columns[0]: "Location"})
        loc_col = "Location"

    rename_map = {}

    candidates_to_dst = [
        (["Written Current", "Written", "Written CY", "Written TY"], "Written Current"),
        (["Written LY", "Written Last Year"], "Written LY"),
        (["Produced Current", "Produced", "Produced CY", "Produced TY"], "Produced Current"),
        (["Produced LY", "Produced Last Year"], "Produced LY"),
        (["Invoiced Current", "Invoiced", "Invoiced CY", "Invoiced TY"], "Invoiced Current"),
        (["Invoiced LY", "Invoiced Last Year"], "Invoiced LY"),
    ]

    for src_list, dst in candidates_to_dst:
        found = _find_col(df_val, src_list)
        if found is not None:
            rename_map[found] = dst

    df_val = df_val.rename(columns=rename_map)

    df_val["Location"] = df_val[loc_col].apply(_canonical_location)
    df_val = df_val.dropna(subset=["Location"])

    numeric_cols = [
        "Written Current", "Written LY",
        "Produced Current", "Produced LY",
        "Invoiced Current", "Invoiced LY",
    ]
    for col_val in numeric_cols:
        df_val = _coerce_numeric(df_val, col_val)

    keep_cols = ["Location"] + [c for c in numeric_cols if c in df_val.columns]
    df_out = df_val[keep_cols].copy()

    df_out["Location"] = df_out["Location"].astype(str).str.strip()
    df_out = df_out[df_out["Location"].str.len() > 0]

    return df_out


def _write_landing_parquets(workbook_path_obj):
    plan_out = _build_landing_plan_df(workbook_path_obj)
    ly_out = _build_landing_ly_df(workbook_path_obj)

    plan_out.to_parquet(PLAN_OUT_PATH, index=False)
    ly_out.to_parquet(LY_OUT_PATH, index=False)

    return plan_out, ly_out


with st.expander("Workbook source", expanded=False):
    url_val = st.secrets.get("DATA_XLSX_URL", "")
    st.write("DATA_XLSX_URL")
    st.code(str(url_val))
    workbook_path = ensure_latest_workbook(ttl_seconds=0)
    workbook_path_obj = Path(str(workbook_path))
    st.write("Local path")
    st.code(str(workbook_path_obj))
    if workbook_path_obj.exists():
        size_mb = workbook_path_obj.stat().st_size / (1024.0 * 1024.0)
        mtime = dt.datetime.fromtimestamp(workbook_path_obj.stat().st_mtime)
        st.write("Last modified")
        st.code(str(mtime))
        st.write("Size MB")
        st.code(str(round(size_mb, 1)))

workbook_path = ensure_latest_workbook(ttl_seconds=0)
workbook_path_obj = Path(str(workbook_path))

xl_obj = pd.ExcelFile(str(workbook_path_obj))
all_sheet_names = xl_obj.sheet_names
allowed_present = [s for s in all_sheet_names if s in ALLOWED_SHEETS]
allowed_missing = [s for s in ALLOWED_SHEETS if s not in all_sheet_names]

with st.expander("Sheet visibility (debug)", expanded=False):
    st.write("All sheets detected in workbook")
    st.write(all_sheet_names)
    st.write("Sheets exposed in UI")
    st.write(allowed_present)
    if len(allowed_missing) > 0:
        st.error("Workbook is missing required sheets: " + str(allowed_missing))
        st.stop()

st.header("Landing data build")

c1, c2, c3 = st.columns([1.2, 1.0, 3.0])
with c1:
    build_btn = st.button("Build Landing parquet files", type="primary")
with c2:
    clear_cache_btn = st.button("Clear cache")
with c3:
    st.caption("Outputs: " + PLAN_OUT_PATH + " and " + LY_OUT_PATH)

if clear_cache_btn:
    st.cache_data.clear()
    st.success("Cache cleared.")

if build_btn:
    with st.spinner("Building landing parquet files from workbook..."):
        plan_out, ly_out = _write_landing_parquets(workbook_path_obj)

    st.cache_data.clear()
    st.success("Landing parquet files written and cache cleared.")

    st.write(PLAN_OUT_PATH + " exists: " + str(os.path.exists(PLAN_OUT_PATH)))
    st.write(LY_OUT_PATH + " exists: " + str(os.path.exists(LY_OUT_PATH)))

    st.subheader("Locations written (sanity check)")
    if "Location" in plan_out.columns:
        st.write(sorted(plan_out["Location"].astype(str).str.strip().unique().tolist()))
    if "Location" in ly_out.columns:
        st.write(sorted(ly_out["Location"].astype(str).str.strip().unique().tolist()))

    st.subheader("Plan parquet preview")
    st.dataframe(plan_out.head(25), use_container_width=True)

    st.subheader("Vs LY parquet preview")
    st.dataframe(ly_out.head(25), use_container_width=True)

    st.rerun()

st.divider()
st.header("Load data")

selected_sheets = st.multiselect(
    "Select sheets to load",
    options=allowed_present,
    default=allowed_present,
)

max_rows = st.number_input(
    "Preview rows per sheet",
    min_value=5,
    max_value=200,
    value=25,
    step=5,
)

show_raw_header_detection = st.checkbox("Show header detection details", value=False)

if len(selected_sheets) == 0:
    st.info("Select at least one sheet above.")
else:
    for sheet_val in selected_sheets:
        st.subheader(sheet_val)
        header_row_idx = _detect_header_row(workbook_path_obj, sheet_val, max_scan_rows=25)

        if show_raw_header_detection:
            st.caption("Detected header row index (0-based)")
            st.code(str(header_row_idx))
            preview_raw = pd.read_excel(
                str(workbook_path_obj),
                sheet_name=sheet_val,
                header=None,
                nrows=int(header_row_idx + 5)
            )
            st.caption("Top rows (raw) used for header detection")
            st.dataframe(preview_raw, use_container_width=True)

        df_sheet = _read_sheet_cached(str(workbook_path_obj), sheet_val, header_row_idx)

        st.caption("Preview (cleaned)")
        st.dataframe(df_sheet.head(int(max_rows)), use_container_width=True)
