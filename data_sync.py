from pathlib import Path
import hashlib
import requests
import streamlit as st

DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "current.xlsx"
ETAG_PATH = DATA_DIR / "current.etag"
HASH_PATH = DATA_DIR / "current.sha256"

def _sha256_bytes(byte_data):
    h = hashlib.sha256()
    h.update(byte_data)
    return h.hexdigest()

def _read_text(path_obj):
    if not path_obj.exists():
        return None
    return path_obj.read_text(encoding="utf-8").strip()

def _write_text(path_obj, txt):
    path_obj.write_text(txt, encoding="utf-8")

def ensure_latest_workbook():
    """
    Downloads the workbook from a configured URL into data/current.xlsx.
    Uses ETag when available; falls back to sha256 to prevent unnecessary writes.
    Config via Streamlit Secrets:
      - st.secrets["DATA_XLSX_URL"]
      - optional st.secrets["DATA_AUTH_HEADER"] (e.g. "Bearer xxx")
    """
    DATA_DIR.mkdir(exist_ok=True)

    if "DATA_XLSX_URL" not in st.secrets:
        return False, "No DATA_XLSX_URL configured in Streamlit secrets"

    url = st.secrets["DATA_XLSX_URL"]
    auth_header = st.secrets.get("DATA_AUTH_HEADER", None)

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    prev_etag = _read_text(ETAG_PATH)
    if prev_etag:
        headers["If-None-Match"] = prev_etag

    resp = requests.get(url, headers=headers, timeout=60)
    if resp.status_code == 304:
        return False, "Workbook unchanged (ETag)"

    resp.raise_for_status()
    content = resp.content

    new_hash = _sha256_bytes(content)
    prev_hash = _read_text(HASH_PATH)
    if prev_hash and prev_hash == new_hash and DATA_PATH.exists():
        return False, "Workbook unchanged (sha256)"

    tmp_path = DATA_DIR / "current.xlsx.tmp"
    tmp_path.write_bytes(content)
    tmp_path.replace(DATA_PATH)

    etag = resp.headers.get("ETag", None)
    if etag:
        _write_text(ETAG_PATH, etag)
    _write_text(HASH_PATH, new_hash)

    return True, "Workbook downloaded and updated"
