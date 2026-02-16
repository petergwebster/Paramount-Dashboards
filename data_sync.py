from pathlib import Path
import time
import zipfile
import requests
import streamlit as st
import pandas as pd

DEST_PATH = Path("data/current.xlsx")

REQUIRED_SHEETS = [
    "Written and Produced by Week",
    "Written Produced Invoiced",
    "YTD Plan vs Act",
    "YTD vs LY",
    "Color Yards",
    "WIP",
    "Yards Wasted",
]

FORBIDDEN_SHEETS = [
    "Sheet1",
]

def _looks_like_xlsx(path_val):
    try:
        with zipfile.ZipFile(path_val, "r") as zf:
            names = zf.namelist()
            return "xl/workbook.xml" in names
    except Exception:
        return False

def _get_sheet_names(path_val):
    xl_obj = pd.ExcelFile(str(path_val))
    return xl_obj.sheet_names

def _enforce_contract(path_val, url_val):
    sheet_names = _get_sheet_names(path_val)

    missing_required = [s for s in REQUIRED_SHEETS if s not in sheet_names]
    forbidden_present = [s for s in FORBIDDEN_SHEETS if s in sheet_names]

    if missing_required or forbidden_present:
        raise RuntimeError(
            "Workbook contract failed. Missing required sheets: "
            + str(missing_required)
            + " Forbidden sheets present: "
            + str(forbidden_present)
            + " URL: "
            + str(url_val)
            + " Sheets detected: "
            + str(sheet_names)
        )

def ensure_latest_workbook(ttl_seconds=0, min_size_bytes=5_000_000):
    """
    Downloads the Excel workbook from st.secrets["DATA_XLSX_URL"] into data/current.xlsx

    ttl_seconds default 0 so you always refresh while debugging.
    min_size_bytes default 5MB so we fail fast if we accidentally download HTML/test data.
    """
    url_val = st.secrets.get("DATA_XLSX_URL", "")
    if str(url_val).strip() == "":
        raise RuntimeError("Missing DATA_XLSX_URL in Streamlit secrets")

    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DEST_PATH.exists() and ttl_seconds is not None and ttl_seconds > 0:
        age_seconds = time.time() - DEST_PATH.stat().st_mtime
        if age_seconds < ttl_seconds:
            if not _looks_like_xlsx(DEST_PATH):
                raise RuntimeError("Cached file does not look like a valid XLSX at " + str(DEST_PATH))
            _enforce_contract(DEST_PATH, url_val="cached")
            return DEST_PATH

    resp = requests.get(url_val, timeout=180, allow_redirects=True)
    resp.raise_for_status()
    content_bytes = resp.content
    byte_len = len(content_bytes)

    DEST_PATH.write_bytes(content_bytes)

    if byte_len < int(min_size_bytes):
        raise RuntimeError(
            "Downloaded file is too small to be the real workbook. Bytes: "
            + str(byte_len)
            + " URL: "
            + str(url_val)
        )

    if not _looks_like_xlsx(DEST_PATH):
        raise RuntimeError(
            "Downloaded file does not look like a valid XLSX (zip missing xl/workbook.xml). "
            + "Bytes: "
            + str(byte_len)
            + " URL: "
            + str(url_val)
        )

    _enforce_contract(DEST_PATH, url_val=url_val)
    return DEST_PATH
