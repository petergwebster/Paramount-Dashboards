from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# Prefer a published/current file if present, otherwise fall back to the static workbook.
PUBLISHED_PATH = Path("data") / "current.xlsx"
FALLBACK_PATH = Path("data") / "WIP Test Data.xlsx"


def _resolve_data_path() -> Path:
    """
    Picks the best available data file.
    """
    if PUBLISHED_PATH.exists():
        return PUBLISHED_PATH
    return FALLBACK_PATH


def _mtime_or_none(path_obj: Path) -> float | None:
    """
    Used only to invalidate Streamlit cache when the file changes.
    """
    try:
        return path_obj.stat().st_mtime
    except Exception:
        return None


@st.cache_data(show_spinner="Loading data...")
def _load_df_cached(data_path_str: str, cache_bust_mtime: float | None) -> pd.DataFrame:
    """
    Internal cached loader. Cache key includes:
    - the resolved file path (as string)
    - the file modified time (so cache refreshes automatically when Excel updates)
    """
    return pd.read_excel(data_path_str)


def load_df(path: str | Path | None = None) -> pd.DataFrame:
    """
    Public loader used by your pages.
    - If `path` is None, uses the resolved data path.
    - If a path is provided, loads that file instead.
    """
    data_path = Path(path) if path is not None else _resolve_data_path()
    return _load_df_cached(str(data_path), _mtime_or_none(data_path))


def show_published_timestamp(path: str | Path | None = None) -> None:
    """
    Shows 'Published data last updated' for whichever file is being used.
    """
    data_path = Path(path) if path is not None else _resolve_data_path()

    try:
        ts = datetime.fromtimestamp(data_path.stat().st_mtime)
        st.caption("Published data last updated: " + ts.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        st.caption("Published data last updated: (timestamp unavailable)")
