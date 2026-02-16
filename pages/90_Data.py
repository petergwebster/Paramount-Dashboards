from pathlib import Path
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
    return s_val

def _is_grand_total(loc_str):
    if loc_str is None:
        return False
    s_val = str(loc_str).strip().lower()
    return s_val == "grand total"

def _is_division_total(loc_str):
    if loc_str is None:
        return False
    s_val = str(loc_str).strip().lower()
    return s_val.endswith(" total") and s_val != "grand total"

def _base_division_name(loc_str):
    if loc_str is None:
        return None
    s_val = str(loc_str).strip()
    s_low = s_val.lower()
    if s_low == "grand total":
        return "Grand Total"
    if s_low.endswith(" total"):
        return s_val[: -len(" total")].strip()
    return s_val

def _make_parquet_safe(df_val):
    # Defensive normalization so pyarrow doesn't fail on mixed types like "2026 Total" in a Year column
    if df_val is None:
        return df_val

    out_df = df_val.copy()
    out_df.columns = [str(c) for c in out_df.columns]

    for c in out_df.columns:
        col_ser = out_df[c]
        c_norm = str(c).strip().lower()

        if "year" in c_norm:
            out_df[c] = col_ser.astype(str).str.strip()
            out_df.loc[out_df[c].str.lower() == "", c] = pd.NA
            continue

        if col_ser.dtype == "object":
            numeric_try = pd.to_numeric(col_ser, errors="coerce")
            non_null = col_ser.notna().sum()
            numeric_rate = 0.0
            if non_null > 0:
                numeric_rate = numeric_try.notna().sum() / non_null

            if numeric_rate >= 0.95:
                out_df[c] = numeric_try
            else:
                out_df[c] = col_ser.astype(str).str.strip()
                out_df.loc[out_df[c].str.lower() == "", c] = pd.NA

    return out_df

def _write_parquet_safe(df_val, out_path):
    safe_df = _make_parquet_safe(df_val)
    safe_df.to_parquet(out_path, index=False)
    return safe_df

def _build_landing_plan_df(workbook_path_obj):
    sheet_name = "YTD Plan vs Act"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    division_col = _find_col(raw_df, ["Division", "Location"])
    if division_col is None:
        division_col = raw_df.columns[0]

    yards_produced_col = _find_col(raw_df, ["Yards Produced", "Produced Yards", "Produced"])
    yards_planned_col = _find_col(raw_df, ["Yards Planned", "Planned Yards", "Plan Yards", "Planned"])
    income_produced_col = _find_col(raw_df, ["Income Produced", "Produced Income", "Produced $", "Produced"])
    income_planned_col = _find_col(raw_df, ["Income Planned", "Planned Income", "Plan Income", "Planned $"])
    net_yards_invoiced_col = _find_col(raw_df, ["Net Yards Invoiced", "Yards Invoiced", "Invoiced Yards"])
    net_income_invoiced_col = _find_col(raw_df, ["Net Income Invoiced", "Income Invoiced", "Invoiced Income", "Invoiced $"])

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

def _build_trend_weekly_df(workbook_path_obj):
    # Weekly trends should come from a sheet that has actual week dates + metrics.
    # We keep it general and just coerce everything except Week to numeric.
    sheet_name = "Written and Produced by Week"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    week_col = _find_col(raw_df, ["Week End", "Week", "Week Ending", "Date"])
    if week_col is None:
        week_col = raw_df.columns[0]

    df_val = raw_df.copy()
    df_val[week_col] = pd.to_datetime(df_val[week_col], errors="coerce")
    df_val = df_val[df_val[week_col].notna()].copy()

    for c in df_val.columns:
        if c == week_col:
            continue
        df_val[c] = pd.to_numeric(df_val[c], errors="coerce")

    keep_cols = [week_col]
    for c in df_val.columns:
        if c == week_col:
            continue
        if df_val[c].notna().any():
            keep_cols.append(c)

    out_df = df_val.loc[:, keep_cols].copy()
    out_df = out_df.sort_values(week_col).reset_index(drop=True)
    out_df = out_df.rename(columns={week_col: "Week"})
    return out_df

def _build_wip_df(workbook_path_obj):
    # WIP is usually already a table. Keep columns, drop all-empty rows/cols, numeric-coerce where possible.
    sheet_name = "WIP"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    df_val = raw_df.copy()
    df_val = df_val.dropna(axis=0, how="all")

    for c in df_val.columns:
        if df_val[c].dtype == "object":
            numeric_try = pd.to_numeric(df_val[c], errors="coerce")
            non_null = df_val[c].notna().sum()
            numeric_rate = 0.0
            if non_null > 0:
                numeric_rate = numeric_try.notna().sum() / non_null
            if numeric_rate >= 0.95:
                df_val[c] = numeric_try

    return df_val.reset_index(drop=True)

def _build_color_yards_df(workbook_path_obj):
    # This sheet often has pivot-style "Year" columns with "2026 Total" values.
    # We keep everything and let _make_parquet_safe() normalize types for parquet write.
    sheet_name = "Color Yards"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    df_val = raw_df.copy()
    df_val = df_val.dropna(axis=0, how="all")
    return df_val.reset_index(drop=True)

def _build_yards_wasted_df(workbook_path_obj):
    sheet_name = "Yards Wasted"
    header_row_idx = _detect_header_row(workbook_path_obj, sheet_name)
    raw_df = _read_sheet_cached(str(workbook_path_obj), sheet_name, header_row_idx)

    df_val = raw_df.copy()
    df_val = df_val.dropna(axis=0, how="all")

    date_col = _find_col(df_val, ["Date", "Day", "Week End", "Week Ending"])
    if date_col is not None:
        df_val[date_col] = pd.to_datetime(df_val[date_col], errors="coerce")

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
