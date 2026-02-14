import os
import datetime
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime

PUBLISHED_PATH = "data/current.xlsx"
DATA_PATH = Path("data/WIP Test Data.xlsx")

@st.cache_data(show_spinner=False)
def load_df(published_path=PUBLISHED_PATH):
    df_local = pd.read_excel(published_path)
    return df_local
@st.cache_data(show_spinner="Loading data...")
def load_df():
    df = pd.read_excel(DATA_PATH)
    return df

def show_published_timestamp(published_path=PUBLISHED_PATH):
def show_published_timestamp():
    try:
        file_mtime = os.path.getmtime(published_path)
        dt_local = datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")
        st.caption("Published data last updated: " + dt_local)
        ts = datetime.fromtimestamp(DATA_PATH.stat().st_mtime)
        st.caption("Published data last updated: " + ts.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        st.caption("Published data last updated: (timestamp unavailable)")
        pass
