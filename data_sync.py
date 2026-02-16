from pathlib import Path
import time
import zipfile
import requests
import streamlit as st

DEST_PATH = Path("data/current.xlsx")

def _looks_like_xlsx(path_val):
    try:
        with zipfile.ZipFile(path_val, "r") as zf:
            names = zf.namelist()
            return "xl/workbook.xml" in names
    except Exception:
        return False

def ensure_latest_workbook(ttl_seconds=0, min_size_bytes=5_000_000):
    """
    Downloads the Excel workbook from st.secrets["DATA_XLSX_URL"] into data/current.xlsx

    ttl_seconds default 0 so you always refresh while debugging.
    min_size_bytes default 5MB so we fail fast if we accidentally download HTML/test data.
    """
    url = st.secrets.get("DATA_XLSX_URL", "")
    if str(url).strip() == "":
        raise RuntimeError("Missing DATA_XLSX_URL in Streamlit secrets")

    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DEST_PATH.exists() and ttl_seconds is not None and ttl_seconds > 0:
        age_seconds = time.time() - DEST_PATH.stat().st_mtime
        if age_seconds < ttl_seconds:
            return DEST_PATH

    resp = requests.get(url, timeout=180, allow_redirects=True)
    resp.raise_for_status()

    content_bytes = resp.content
    byte_len = len(content_bytes)

    # write
    DEST_PATH.write_bytes(content_bytes)

    # validate size
    if byte_len < int(min_size_bytes):
        raise RuntimeError(
            "Downloaded file is too small to be the real workbook. Bytes: "
            + str(byte_len)
            + " URL: "
            + str(url)
        )

    # validate is actually an XLSX
    if not _looks_like_xlsx(DEST_PATH):
        raise RuntimeError(
            "Downloaded file does not look like a valid XLSX (zip missing xl/workbook.xml). "
            + "Bytes: "
            + str(byte_len)
            + " URL: "
            + str(url)
        )

    return DEST_PATH
