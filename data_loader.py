import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# Prefer a published/current file if present, otherwise fall back to the static workbook.
PUBLISHED_PATH = Path("data") / "current.xlsx"
FALLBACK_PATH = Path("data") / "WIP Test Data.xlsx"


def _resolve_data_path() -> Path:
    """
    Return the path we should actually load:
    - data/current.xlsx if it exists
    - otherwise data/WIP Test Data.xlsx
    """
    if PUBLISHED_PATH.exists():
        return PUBLISHED_PATH
    return FALLBACK_PATH


@st.cache_data(show_spinner="Loading data...")
def load_df(path: str | Path | None = None) -> pd.DataFrame:
    """
    Load the main dataframe, with caching.

    If `path` is None, use _resolve_data_path().
    You can pass an explicit path if you ever want to override.
    """
    if path is None:
        data_path = _resolve_data_path()
    else:
        data_path = Path(path)

    df = pd.read_excel(data_path)
    return df


def show_published_timestamp(path: str | Path | None = None) -> None:
    """
    Show a 'Published data last updated' timestamp in the app.

    If `path` is None, it uses the same logic as _resolve_data_path().
    """
    try:
        if path is None:
            data_path = _resolve_data_path()
        else:
            data_path = Path(path)

        ts = datetime.fromtimestamp(data_path.stat().st_mtime)
        st.caption("Published data last updated: " + ts.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        st.caption("Published data last updated: (timestamp unavailable)")
