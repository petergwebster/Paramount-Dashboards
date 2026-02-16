from pathlib import Path
import time
import requests

import streamlit as st

DEST_PATH = Path("data/current.xlsx")

def _download(url, dest_path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest_path.write_bytes(resp.content)
    return dest_path

def ensure_latest_workbook(ttl_seconds=300):
    """
    Uses Streamlit secrets:
      DATA_XLSX_URL = "https://....dashboard.xlsx"

    Downloads to:
      data/current.xlsx

    Returns a local Path.
    """
    url = st.secrets.get("DATA_XLSX_URL", None)
    if url is None or str(url).strip() == "":
        raise RuntimeError("Missing DATA_XLSX_URL in Streamlit secrets")

    if DEST_PATH.exists():
        age_seconds = time.time() - DEST_PATH.stat().st_mtime
        if age_seconds < ttl_seconds:
            return DEST_PATH

    return _download(url, DEST_PATH)
