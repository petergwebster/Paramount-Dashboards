import os
import datetime
import pandas as pd
import streamlit as st

PUBLISHED_PATH = "data/current.xlsx"

@st.cache_data(show_spinner=False)
def load_df(published_path=PUBLISHED_PATH):
    df_local = pd.read_excel(published_path)
    return df_local

def show_published_timestamp(published_path=PUBLISHED_PATH):
    try:
        file_mtime = os.path.getmtime(published_path)
        dt_local = datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")
        st.caption("Published data last updated: " + dt_local)
    except Exception:
        st.caption("Published data last updated: (timestamp unavailable)")
