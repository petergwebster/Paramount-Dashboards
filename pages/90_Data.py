from pathlib import Path
import os
import re
import streamlit as st
import pandas as pd

from data_sync import ensure_latest_workbook

st.set_page_config(page_title="Data", layout="wide")
st.title("Admin - Data")

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
        nrows=int(max_scan_rows)
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

def _norm_key(col_name):
    return str(col_name).strip().lower().replace(" ", "_").replace("-", "_")

def _find_col(df_val, candidates):
    if df_val is None or len(df_val.columns) == 0:
        return None
    norm_map = {_norm_key(c): c for c in df_val.columns}
    for cand in candidates:
        cand_norm = _norm_key(cand)
        if cand_norm in norm_map:
            return norm_map[cand_norm]
    return None

def _clean_loc(loc_val):
    if pd.isna(loc_val):
        return None
    s_val = str(loc_val).strip()
    if s_val == "":
        return None
    if s_val.lower() == "":
        return None
    return s_val

def _is_grand_total(loc_str):
    if loc_str is None:
        return False
    return str(loc_str).strip().lower() == "grand total"

def _is_division_total(loc_str):
    if loc_str is None:
        return False
    s_val = str(loc_str).strip().lower()
    if s_val == "grand total":
        return False
    return s_val.endswith(" total")

def _base_division_name(loc_str):
    if loc_str is None:
        return None
    s_val = str(loc_str).strip()
    s_low = s_val.lower()
    if s_low.endswith(" total") and s_low != "grand total":
        return s_val[: -len(" total")].strip()
    return s_val

def _build_landing_plan_df(workbook_path_obj):
    sheet_name = "YTD Plan vs Act"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    division_col = _find_col(raw_df, ["Division", "Location"])
    if division_col is None:
        division_col = raw_df.columns[0]

    yards_produced_col = _find_col(raw_df, ["Yards Produced"])
    yards_planned_col = _find_col(raw_df, ["Yards Planned"])
    income_produced_col = _find_col(raw_df, ["Income Produced"])
    income_planned_col = _find_col(raw_df, ["Income Planned"])
    net_yards_invoiced_col = _find_col(raw_df, ["Net Yards Invoiced"])
    net_income_invoiced_col = _find_col(raw_df, ["Net Income Invoiced"])

    keep_cols = [division_col]
    for c in [
        yards_produced_col,
        yards_planned_col,
        income_produced_col,
        income_planned_col,
        net_yards_invoiced_col,
        net_income_invoiced_col,
    ]:
        if c is not None and c not in keep_cols:
            keep_cols.append(c)

    df_val = raw_df.loc[:, keep_cols].copy()
    df_val[division_col] = df_val[division_col].apply(_clean_loc)

    for c in keep_cols:
        if c != division_col:
            df_val[c] = pd.to_numeric(df_val[c], errors="coerce")

    df_val["__is_grand_total"] = df_val[division_col].apply(_is_grand_total)
    df_val["__is_div_total"] = df_val[division_col].apply(_is_division_total)

    totals_df = df_val[df_val["__is_grand_total"] | df_val["__is_div_total"]].copy()

    totals_df["Location"] = totals_df[division_col].apply(_base_division_name)
    totals_df["Location"] = totals_df["Location"].apply(_clean_loc)

    totals_df = totals_df[totals_df["Location"].notna()].copy()
    totals_df = totals_df[~totals_df["Location"].astype(str).str.strip().str.lower().isin(EXCLUDE_DIVISIONS)].copy()

    out_df = pd.DataFrame()
    out_df["Location"] = totals_df["Location"]

    if yards_produced_col is not None:
        out_df["Yards Produced"] = totals_df[yards_produced_col]
    if yards_planned_col is not None:
        out_df["Yards Planned"] = totals_df[yards_planned_col]
    if income_produced_col is not None:
        out_df["Income Produced"] = totals_df[income_produced_col]
    if income_planned_col is not None:
        out_df["Income Planned"] = totals_df[income_planned_col]
    if net_yards_invoiced_col is not None:
        out_df["Net Yards Invoiced"] = totals_df[net_yards_invoiced_col]
    if net_income_invoiced_col is not None:
        out_df["Net Income Invoiced"] = totals_df[net_income_invoiced_col]

    out_df = out_df.dropna(how="all", subset=[c for c in out_df.columns if c != "Location"])

    out_df["__sort"] = out_df["Location"].astype(str).str.strip().str.lower().apply(lambda x: 9999 if x == "grand total" else 0)
    out_df = out_df.sort_values(["__sort", "Location"]).drop(columns=["__sort"]).reset_index(drop=True)

    out_df = out_df.drop_duplicates(subset=["Location"], keep="last").reset_index(drop=True)

    return out_df

def _build_landing_vs_ly_df(workbook_path_obj):
    sheet_name = "YTD vs LY"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    division_col = _find_col(raw_df, ["Division", "Location"])
    if division_col is None:
        division_col = raw_df.columns[0]

    produced_current_col = _find_col(raw_df, ["Produced", "Produced Current", "Income Produced", "Produced TY", "TY Produced"])
    produced_ly_col = _find_col(raw_df, ["Produced LY", "LY Produced", "Income Produced LY", "Produced Last Year"])
    invoiced_current_col = _find_col(raw_df, ["Invoiced", "Invoiced Current", "Net Income Invoiced", "Invoiced TY", "TY Invoiced"])
    invoiced_ly_col = _find_col(raw_df, ["Invoiced LY", "LY Invoiced", "Net Income Invoiced LY", "Invoiced Last Year"])

    keep_cols = [division_col]
    for c in [produced_current_col, produced_ly_col, invoiced_current_col, invoiced_ly_col]:
        if c is not None and c not in keep_cols:
            keep_cols.append(c)

    df_val = raw_df.loc[:, keep_cols].copy()
    df_val[division_col] = df_val[division_col].apply(_clean_loc)

    for c in keep_cols:
        if c != division_col:
            df_val[c] = pd.to_numeric(df_val[c], errors="coerce")

    df_val["__is_grand_total"] = df_val[division_col].apply(_is_grand_total)
    df_val["__is_div_total"] = df_val[division_col].apply(_is_division_total)

    totals_df = df_val[df_val["__is_grand_total"] | df_val["__is_div_total"]].copy()

    totals_df["Location"] = totals_df[division_col].apply(_base_division_name)
    totals_df["Location"] = totals_df["Location"].apply(_clean_loc)

    totals_df = totals_df[totals_df["Location"].notna()].copy()
    totals_df = totals_df[~totals_df["Location"].astype(str).str.strip().str.lower().isin(EXCLUDE_DIVISIONS)].copy()

    out_df = pd.DataFrame()
    out_df["Location"] = totals_df["Location"]

    if produced_current_col is not None:
        out_df["Produced Current"] = totals_df[produced_current_col]
    if produced_ly_col is not None:
        out_df["Produced LY"] = totals_df[produced_ly_col]
    if invoiced_current_col is not None:
        out_df["Invoiced Current"] = totals_df[invoiced_current_col]
    if invoiced_ly_col is not None:
        out_df["Invoiced LY"] = totals_df[invoiced_ly_col]

    out_df = out_df.dropna(how="all", subset=[c for c in out_df.columns if c != "Location"])

    out_df["__sort"] = out_df["Location"].astype(str).str.strip().str.lower().apply(lambda x: 9999 if x == "grand total" else 0)
    out_df = out_df.sort_values(["__sort", "Location"]).drop(columns=["__sort"]).reset_index(drop=True)

    out_df = out_df.drop_duplicates(subset=["Location"], keep="last").reset_index(drop=True)

    return out_df

def _write_landing_parquets(workbook_path_obj):
    plan_df_val = _build_landing_plan_df(workbook_path_obj)
    ly_df_val = _build_landing_vs_ly_df(workbook_path_obj)

    plan_df_val.to_parquet(PLAN_OUT_PATH, index=False)
    ly_df_val.to_parquet(LY_OUT_PATH, index=False)

    return plan_df_val, ly_df_val

with st.sidebar:
    st.header("Workbook")
    workbook_path = ensure_latest_workbook()
    st.code(str(workbook_path))

st.header("Landing data build")
st.caption("Writes " + PLAN_OUT_PATH + " and " + LY_OUT_PATH)

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
    st.success("Parquets written and cache cleared.")

    st.subheader("Plan parquet (what Landing uses)")
    st.dataframe(plan_out_df, use_container_width=True)

    st.subheader("Vs LY parquet (what Landing uses)")
    st.dataframe(ly_out_df, use_container_width=True)

    st.subheader("Locations written (sanity check)")
    if "Location" in plan_out_df.columns:
        st.write(plan_out_df["Location"].tolist())
    if "Location" in ly_out_df.columns:
        st.write(ly_out_df["Location"].tolist())

    st.rerun()

st.divider()
st.header("Sheet preview")

sheet_name_choice = st.selectbox("Sheet", ALLOWED_SHEETS, index=ALLOWED_SHEETS.index("YTD Plan vs Act"))
header_row_idx = _detect_header_row(workbook_path, sheet_name_choice, max_scan_rows=35)
df_preview = _read_sheet_cached(str(workbook_path), sheet_name_choice, header_row_idx)

st.caption("Detected header row index " + str(header_row_idx))
st.dataframe(df_preview.head(50), use_container_width=True)
