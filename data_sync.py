from pathlib import Path
import hashlib
import requests
import streamlit as st

DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "current.xlsx"

def _sha256_bytes(blob):
    h = hashlib.sha256()
    h.update(blob)
    return h.hexdigest()

def ensure_latest_workbook():
    """
    Downloads the workbook from st.secrets["DATA_XLSX_URL"] into data/current.xlsx
    Returns updated_bool, message_str
    """
    DATA_DIR.mkdir(exist_ok=True)

    url = st.secrets.get("DATA_XLSX_URL", "")
    if not url:
        return False, "No DATA_XLSX_URL set in Streamlit Secrets."

    headers = {}
    bearer = st.secrets.get("DATA_BEARER_TOKEN", "")
    if bearer:
        headers["Authorization"] = "Bearer " + bearer

    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    blob = resp.content

    if len(blob) < 2000:
        first_bytes = blob[:200].decode("utf-8", errors="ignore")
        if "<html" in first_bytes.lower():
            return False, "Downloaded HTML not XLSX check DATA_XLSX_URL permissions."

    new_hash = _sha256_bytes(blob)

    if DATA_PATH.exists():
        old_blob = DATA_PATH.read_bytes()
        old_hash = _sha256_bytes(old_blob)
        if old_hash == new_hash:
            return False, "Workbook already up to date."
        DATA_PATH.write_bytes(blob)
        return True, "Workbook updated."

    DATA_PATH.write_bytes(blob)
    return True, "Workbook downloaded."
