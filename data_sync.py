from pathlib import Path
import time
import requests
import streamlit as st

DEST_PATH = Path("data/current.xlsx")

def ensure_latest_workbook(ttl_seconds=300):
    """
    Source of truth: st.secrets["DATA_XLSX_URL"]
    Local cache: data/current.xlsx

    Returns: Path to local workbook.
    """
    url = st.secrets.get("DATA_XLSX_URL", "")
    if str(url).strip() == "":
        raise RuntimeError("Missing DATA_XLSX_URL in Streamlit secrets")

    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DEST_PATH.exists():
        age_seconds = time.time() - DEST_PATH.stat().st_mtime
        if age_seconds < ttl_seconds:
            return DEST_PATH

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    DEST_PATH.write_bytes(resp.content)
    return DEST_PATH
