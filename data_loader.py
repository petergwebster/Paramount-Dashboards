import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime

DATA_PATH = Path("data/WIP Test Data.xlsx")

@st.cache_data(show_spinner="Loading data...")
def load_df():
    df = pd.read_excel(DATA_PATH)
    return df

def show_published_timestamp():
    try:
        ts = datetime.fromtimestamp(DATA_PATH.stat().st_mtime)
        st.caption("Published data last updated: " + ts.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        pass
