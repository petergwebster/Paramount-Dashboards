from pathlib import Path
import time

import requests

try:
    import streamlit as st
except Exception:
    class _StubStreamlit:
        def __getattr__(self, name):
            def _noop(*args, **kwargs):
                return None
            return _noop
    st = _StubStreamlit()

# Local destination for the workbook
DEST_PATH = Path("data/current.xlsx")


def _download_if_needed(url: str, dest: Path, ttl_seconds: int = 300) -> Path:
    """
    Download the Excel workbook from `url` to `dest` if:
      - dest does not exist, or
      - dest is older than `ttl_seconds`.

    Returns the Path to the local file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    needs_download = True
    if dest.exists():
        age = time.time() - dest.stat().st_mtime
        if age < ttl_seconds:
            needs_download = False

    if not needs_download:
        return dest

    resp = requests.get(url)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def ensure_latest_workbook(ttl_seconds: int = 300) -> Path:
    """
    Read the DATA_XLSX_URL from st.secrets, download if needed,
    and return the local path to the workbook.
    """
    try:
        url = st.secrets["DATA_XLSX_URL"]
    except Exception as e:
        raise RuntimeError("Missing DATA_XLSX_URL in Streamlit secrets") from e

    return _download_if_needed(url, DEST_PATH, ttl_seconds=ttl_seconds)
