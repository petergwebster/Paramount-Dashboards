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

FORBIDDEN_SHEETS = ["Sheet1"]


def _looks_like_xlsx(path_val):
    try:
        with zipfile.ZipFile(path_val, "r") as zf:
            names = zf.namelist()
            return "xl/workbook.xml" in names
    except Exception:
        return False


def _sheet_names(path_val):
    xl_obj = pd.ExcelFile(str(path_val))
    return xl_obj.sheet_names


def ensure_latest_workbook(ttl_seconds=0, min_size_bytes=5_000_000):
    """
    Downloads the Excel workbook from st.secrets["DATA_XLSX_URL"] into data/current.xlsx

    Hard-coded Releases contract:
    - must contain REQUIRED_SHEETS
    - must not contain FORBIDDEN_SHEETS (Sheet1)
    """
    url = st.secrets.get("DATA_XLSX_URL", "")
    if str(url).strip() == "":
        raise RuntimeError("Missing DATA_XLSX_URL in Streamlit secrets")

    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DEST_PATH.exists() and ttl_seconds is not None and ttl_seconds > 0:
        age_seconds = time.time() - DEST_PATH.stat().st_mtime
        if age_seconds < ttl_seconds:
            # If we're using cache, still enforce contract so we never run on bad cached data
            if not _looks_like_xlsx(DEST_PATH):
                raise RuntimeError("Cached file is not a valid XLSX at " + str(DEST_PATH))
            sheet_names = _sheet_names(DEST_PATH)
            missing_required = [s for s in REQUIRED_SHEETS if s not in sheet_names]
            forbidden_present = [s for s in FORBIDDEN_SHEETS if s in sheet_names]
            if len(missing_required) > 0 or len(forbidden_present) > 0:
                raise RuntimeError(
                    "Cached workbook does not match Releases contract. Missing: "
                    + str(missing_required)
                    + " Forbidden present: "
                    + str(forbidden_present)
                )
            return DEST_PATH

    resp = requests.get(url, timeout=180, allow_redirects=True)
    resp.raise_for_status()
    content_bytes = resp.content
    byte_len = len(content_bytes)

    DEST_PATH.write_bytes(content_bytes)

    if byte_len < int(min_size_bytes):
        raise RuntimeError(
            "Downloaded file is too small to be the real workbook. Bytes: "
            + str(byte_len)
            + " URL: "
            + str(url)
        )

    if not _looks_like_xlsx(DEST_PATH):
        raise RuntimeError(
            "Downloaded file does not look like a valid XLSX (zip missing xl/workbook.xml). "
            + "Bytes: "
            + str(byte_len)
            + " URL: "
            + str(url)
        )

    sheet_names = _sheet_names(DEST_PATH)
    missing_required = [s for s in REQUIRED_SHEETS if s not in sheet_names]
    forbidden_present = [s for s in FORBIDDEN_SHEETS if s in sheet_names]

    if len(missing_required) > 0 or len(forbidden_present) > 0:
        raise RuntimeError(
            "Downloaded workbook does not match Releases contract. Missing: "
            + str(missing_required)
            + " Forbidden present: "
            + str(forbidden_present)
            + " URL: "
            + str(url)
        )

    return DEST_PATH
