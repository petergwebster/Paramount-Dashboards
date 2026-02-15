import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Cockpit", layout="wide")

def _to_num(series_in):
    return pd.to_numeric(series_in, errors="coerce")

st.title("Cockpit")
st.write("Helpers loaded ok.")
