import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Debug", layout="wide")
st.title("Debug")

target_path = Path("pages/00_Landing_YTD.py")
st.write("Reading file")
st.code(str(target_path))

if not target_path.exists():
    st.error("File not found")
    st.stop()

code_text = target_path.read_text(errors="ignore")

st.subheader("First 120 lines of pages/00_Landing_YTD.py")
lines = code_text.splitlines()
preview = "\n".join([str(i + 1).rjust(4) + "  " + lines[i] for i in range(min(120, len(lines)))])
st.code(preview, language="python")

st.subheader("Search for the broken token")
st.write("Contains `np.`")
st.write("np." in code_text)
