import os
import pandas as pd
import streamlit as st

def _file_mtime(path_val):
    if not os.path.exists(path_val):
        return None
    return os.path.getmtime(path_val)

@st.cache_data(show_spinner=False)
def _read_parquet_cached(path_val, mtime_val):
    df_val = pd.read_parquet(path_val)
    return df_val

def read_parquet(path_val):
    mtime_val = _file_mtime(path_val)
    if mtime_val is None:
        return None
    return _read_parquet_cached(path_val, mtime_val)
