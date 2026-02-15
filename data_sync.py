from pathlib import Path
import os
import requests
import streamlit as st

DATA_DIR = Path("data")
LOCAL_XLSX_PATH = DATA_DIR / "current.xlsx"


def _get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.environ.get(name, default)


def ensure_latest_workbook():
    """
    Downloads the Excel workbook from DATA_XLSX_URL (Streamlit secrets) to data/current.xlsx.

    Returns
    - updated bool
    - message str
    """
    url = _get_secret("DATA_XLSX_URL", None)
    if url is None or str(url).strip() == "":
        return False, "DATA_XLSX_URL not set in Secrets."

    auth_header = _get_secret("DATA_AUTH_HEADER", "")
    headers = {}
    if auth_header is not None and str(auth_header).strip() != "":
        headers["Authorization"] = str(auth_header).strip()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
    except Exception as exc:
        return False, "Download failed: " + str(exc)

    content_type = str(resp.headers.get("Content-Type", "")).lower()
    content_bytes = resp.content

    if "text/html" in content_type or content_bytes[:20].lower().find(b"<html") != -1:
        return False, "URL returned HTML, not an .xlsx. Check DATA_XLSX_URL is a direct download link."

    old_size = LOCAL_XLSX_PATH.stat().st_size if LOCAL_XLSX_PATH.exists() else -1
    new_size = len(content_bytes)

    if old_size == new_size and old_size > 0:
        return False, "No change detected. File already up to date."

    LOCAL_XLSX_PATH.write_bytes(content_bytes)
    return True, "Downloaded workbook to " + str(LOCAL_XLSX_PATH) + " (" + str(round(new_size / (1024 * 1024), 2)) + " MB)"
