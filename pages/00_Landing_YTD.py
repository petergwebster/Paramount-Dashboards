import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Landing - YTD", layout="wide")
st.title("YTD Scoreboard")

LY_OUT_PATH = "landing_ytd_vs_ly.parquet"

df_val = pd.read_parquet(LY_OUT_PATH)

if "Location" not in df_val.columns:
    df_val["Location"] = ""

df_val["Location"] = df_val["Location"].astype(str).str.strip()

num_cols = [
    "Written LY",
    "Written Current",
    "Produced LY",
    "Produced Current",
    "Invoiced LY",
    "Invoiced Current",
]

for c in num_cols:
    if c in df_val.columns:
        df_val[c] = pd.to_numeric(df_val[c], errors="coerce")
    else:
        df_val[c] = np.

st.dataframe(df_val, width="stretch")
