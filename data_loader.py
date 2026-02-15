import pandas as pd
import streamlit as st
from pathlib import Path

DATA_PATH_DEFAULT = Path("data/current.xlsx")


def _nonempty_count(vals):
    s = vals.astype(str).str.strip()
    s = s.replace("", "")
    return int(s.ne("").sum())


def clean_pivot_export_sheet(xl_obj, sheet_name, min_text_cells=4):
    df_raw = pd.read_excel(xl_obj, sheet_name=sheet_name, header=None)

    row_counts = df_raw.apply(lambda r: _nonempty_count(r), axis=1)
    header_row_idx = int((row_counts >= min_text_cells).idxmax())

    new_cols = [str(x).strip() for x in df_raw.iloc[header_row_idx].tolist()]
    df = df_raw.iloc[header_row_idx + 1 :].copy()
    df.columns = new_cols

    # Drop fully empty rows
    keep_row = df.apply(lambda r: _nonempty_count(r) > 0, axis=1)
    df = df.loc[keep_row].reset_index(drop=True)

    # Drop fully empty columns
    keep_col = df.apply(
        lambda c: c.astype(str).str.strip().replace("", "").ne("").any(),
        axis=0,
    )
    df = df.loc[:, keep_col]

    # De-duplicate column names if needed
    cols = pd.Series(df.columns)
    if cols.duplicated().any():
        seen = {}
        new_names = []
        for c in df.columns:
            if c not in seen:
                seen[c] = 0
                new_names.append(c)
            else:
                seen[c] += 1
                new_names.append(str(c) + "_" + str(seen[c]))
        df.columns = new_names

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
    xlsx_path = Path(xlsx_path_str) if xlsx_path_str else DATA_PATH_DEFAULT
    xl_obj = pd.ExcelFile(xlsx_path)

    sheets = xl_obj.sheet_names
    if selected_sheets is not None:
        sheets = [s for s in sheets if s in set(selected_sheets)]

    tables = {}
    meta_rows = []

    for sn in sheets:
        try:
            df, meta = clean_pivot_export_sheet(
                xl_obj, sn, min_text_cells=min_text_cells
            )
            tables[sn] = df
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
    return tables, meta_df, xl_obj.sheet_names
