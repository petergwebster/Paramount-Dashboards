from pathlib import Path
import pandas as pd
import streamlit as st

DATA_DIR = Path("data")
DATA_PATH_DEFAULT = DATA_DIR / "current.xlsx"


def _nonempty_count(vals):
    s = vals.astype(str).str.strip()
    s = s.replace("", "")
    return int(s.ne("").sum())


def clean_pivot_export_sheet(xl_obj, sheet_name, min_text_cells=4):
    """
    Reads a pivot-export style sheet that usually has a few filter rows on top,
    then a real header row, then data.
    Detects the header row by finding the first row with >= min_text_cells non-empty cells.
    """
    df_raw = pd.read_excel(xl_obj, sheet_name=sheet_name, header=None)

    row_counts = df_raw.apply(lambda r: _nonempty_count(r), axis=1)
    header_row_idx = int((row_counts >= min_text_cells).idxmax())

    new_cols = [str(x).strip() for x in df_raw.iloc[header_row_idx].tolist()]
    df = df_raw.iloc[header_row_idx + 1 :].copy()
    df.columns = new_cols

    keep_row = df.apply(lambda r: _nonempty_count(r) > 0, axis=1)
    df = df.loc[keep_row].reset_index(drop=True)

    keep_col = df.apply(
        lambda c: c.astype(str).str.strip().replace("", "").ne("").any(),
        axis=0,
    )
    df = df.loc[:, keep_col]

    col_series = pd.Series(df.columns)
    if col_series.duplicated().any():
        deduped_cols = []
        seen = {}
        for c in df.columns:
            if c not in seen:
                seen[c] = 0
                deduped_cols.append(c)
            else:
                seen[c] += 1
                deduped_cols.append(c + "_" + str(seen[c]))
        df.columns = deduped_cols

    meta = {
        "sheet": sheet_name,
        "header_row_idx": header_row_idx,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "columns_preview": ", ".join([str(c) for c in df.columns.tolist()[:12]]),
    }
    return df, meta


@st.cache_data(show_spinner=False)
def load_workbook_tables(xlsx_path_str=None, selected_sheets=None, min_text_cells=4):
    """
    Loads an Excel workbook and returns:
      - tables: dict of {sheet_name: cleaned_df}
      - meta_df: summary dataframe for verification
      - sheet_names: list of all sheet names in the workbook
    """
    DATA_DIR.mkdir(exist_ok=True)

    xlsx_path = Path(xlsx_path_str) if xlsx_path_str else DATA_PATH_DEFAULT
    xl_obj = pd.ExcelFile(xlsx_path)

    sheet_names = xl_obj.sheet_names
    use_sheets = sheet_names
    if selected_sheets is not None:
        selected_set = set(selected_sheets)
        use_sheets = [s for s in sheet_names if s in selected_set]

    tables = {}
    meta_rows = []
    for sn in use_sheets:
        try:
            df_clean, meta = clean_pivot_export_sheet(
                xl_obj, sn, min_text_cells=min_text_cells
            )
            tables[sn] = df_clean
            meta_rows.append(meta)
        except Exception as e:
            meta_rows.append(
                {
                    "sheet": sn,
                    "header_row_idx": None,
                    "rows": None,
                    "cols": None,
                    "columns_preview": "ERROR: " + str(e),
                }
            )

    meta_df = pd.DataFrame(meta_rows).sort_values("sheet").reset_index(drop=True)
    return tables, meta_df, sheet_names


def show_published_timestamp(xlsx_path_str=None):
    """
    Backwards-compatible helper used by existing pages.
    """
    xlsx_path = Path(xlsx_path_str) if xlsx_path_str else DATA_PATH_DEFAULT
    if not xlsx_path.exists():
        st.caption("No workbook found at " + str(xlsx_path))
        return

    mod_ts = pd.to_datetime(xlsx_path.stat().st_mtime, unit="s")
    st.caption("Data file last updated: " + str(mod_ts))


@st.cache_data(show_spinner=False)
def load_df(sheet_name=None, xlsx_path_str=None, min_text_cells=4):
    """
    Backwards-compatible function used by existing pages.
    - If sheet_name is None: returns the first sheet.
    - If sheet_name is provided: returns that sheet cleaned.
    """
    xlsx_path = Path(xlsx_path_str) if xlsx_path_str else DATA_PATH_DEFAULT
    if not xlsx_path.exists():
        return pd.DataFrame()

    tables, _, sheet_names = load_workbook_tables(
        str(xlsx_path), selected_sheets=None, min_text_cells=min_text_cells
    )

    if sheet_name is None:
        if len(sheet_names) == 0:
            return pd.DataFrame()
        sheet_name = sheet_names[0]

    df_out = tables.get(sheet_name)
    if df_out is None:
        return pd.DataFrame()

    return df_out
