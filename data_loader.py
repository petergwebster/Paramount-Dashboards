import pandas as pd
from openpyxl import load_workbook


def _load_all_sheets_as_tables(xlsx_path, selected_sheets=None):
    wb = load_workbook(xlsx_path, data_only=True)
    sheet_names = wb.sheetnames

    if selected_sheets is not None and len(selected_sheets) > 0:
        sheet_names = [s for s in sheet_names if s in selected_sheets]

    tables = {}
    meta_rows = []

    for sheet_name in sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

        key = "sheet::" + str(sheet_name)
        tables[key] = df

        meta_rows.append(
            {
                "key": key,
                "sheet_name": str(sheet_name),
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
            }
        )

    meta_df = pd.DataFrame(meta_rows)
    return tables, meta_df, wb.sheetnames


def load_workbook_tables(xlsx_path, selected_sheets=None, min_text_cells=4):
    """
    Main loader used by Streamlit pages.

    Behavior
    - Loads all sheets as DataFrames
    - Applies a lightweight heuristic filter to keep only "table-like" sheets
    - If filtering results in 0 tables, falls back to returning ALL sheets
      so the app is never blocked
    """

    tables_all, meta_all, all_sheets = _load_all_sheets_as_tables(
        xlsx_path, selected_sheets=selected_sheets
    )

    tables_filtered = {}
    meta_rows = []

    for key in list(tables_all.keys()):
        df = tables_all[key]

        if df is None:
            continue

        if df.shape[0] == 0 or df.shape[1] == 0:
            continue

        df_head = df.head(25)

        non_null_cells = int(df_head.notna().sum().sum())
        if non_null_cells < 20:
            continue

        text_like_cells = 0
        try:
            obj_df = df_head.select_dtypes(include=["object"])
            text_like_cells = int(obj_df.notna().sum().sum())
        except Exception:
            text_like_cells = 0

        if text_like_cells < int(min_text_cells):
            continue

        tables_filtered[key] = df

        sheet_name_val = ""
        if key.startswith("sheet::"):
            sheet_name_val = key.replace("sheet::", "")

        meta_rows.append(
            {
                "key": key,
                "sheet_name": sheet_name_val,
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
                "non_null_cells_head25": non_null_cells,
                "text_like_cells_head25": text_like_cells,
            }
        )

    meta_df = pd.DataFrame(meta_rows)

    if len(tables_filtered) == 0:
        meta_all_copy = meta_all.copy()
        meta_all_copy["note"] = "fallback_all_sheets"
        return tables_all, meta_all_copy, all_sheets

    return tables_filtered, meta_df, all_sheets
