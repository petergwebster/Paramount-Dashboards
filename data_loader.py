import pandas as pd
import streamlit as st
from pathlib import Path

DATA_PATH_DEFAULT = Path('data/current.xlsx')


def _row_text_count(row_vals):
    ser = row_vals.astype(str).str.strip()
    ser = ser.replace('', '')
    return int(ser.ne('').sum())


def clean_pivot_export_sheet(xl_obj, sheet_name, min_text_cells=4):
    df_raw = pd.read_excel(xl_obj, sheet_name=sheet_name, header=None)

    row_text_counts = df_raw.apply(lambda r: _row_text_count(r), axis=1)
    header_row_idx = int((row_text_counts >= min_text_cells).idxmax())

    new_cols = [str(x).strip() for x in df_raw.iloc[header_row_idx].tolist()]
    df_clean = df_raw.iloc[header_row_idx + 1:].copy()
    df_clean.columns = new_cols

    # Drop fully empty rows/cols
    nonempty_row_mask = df_clean.apply(lambda r: _row_text_count(r) > 0, axis=1)
    df_clean = df_clean.loc[nonempty_row_mask].reset_index(drop=True)

    nonempty_col_mask = df_clean.apply(
        lambda c: c.astype(str).str.strip().replace('', '').ne('').any(),
        axis=0
    )
    df_clean = df_clean.loc[:, nonempty_col_mask]

    # De-duplicate column names
    col_series = pd.Series(df_clean.columns)
    if col_series.duplicated().any():
        deduped_cols = []
        seen = {}
        for c in df_clean.columns:
            if c not in seen:
                seen[c] = 0
                deduped_cols.append(c)
            else:
                seen[c] += 1
                deduped_cols.append(c + '_' + str(seen[c]))
        df_clean.columns = deduped_cols

    meta = {
        'sheet': sheet_name,
        'header_row_idx': header_row_idx,
        'rows': int(df_clean.shape[0]),
        'cols': int(df_clean.shape[1]),
        'columns_preview': ', '.join([str(c) for c in df_clean.columns.tolist()[:12]])
    }
    return df_clean, meta


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
            df_clean, meta = clean_pivot_export_sheet(xl_obj, sn, min_text_cells=min_text_cells)
            tables[sn] = df_clean
            meta_rows.append(meta)
        except Exception as e:
            meta_rows.append({
                'sheet': sn,
                'header_row_idx': None,
                'rows': None,
                'cols': None,
                'columns_preview': 'ERROR: ' + str(e)
            })

    meta_df = pd.DataFrame(meta_rows).sort_values('sheet').reset_index(drop=True)
    return tables, meta_df, xl_obj.sheet_names
