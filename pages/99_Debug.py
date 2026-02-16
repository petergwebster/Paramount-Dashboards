import streamlit as st
from pathlib import Path
import traceback

st.set_page_config(page_title="Debug", layout="wide")
st.title("Debug")

target_path = Path("pages/00_Landing_YTD.py")
st.write("Reading file")
st.code(str(target_path))

if not target_path.exists():
    st.error("File not found: " + str(target_path))
    st.stop()

code_text = target_path.read_text(errors="ignore")

st.subheader("First 140 lines of pages/00_Landing_YTD.py")
lines = code_text.splitlines()
max_lines = min(140, len(lines))
preview = "\n".join([str(i + 1).rjust(4) + "  " + lines[i] for i in range(max_lines)])
st.code(preview, language="python")

st.subheader("Search for common broken tokens")
st.write("Contains `np.`")
st.write("np." in code_text)

st.write("Contains `= np.`")
st.write("= np." in code_text)

st.subheader("Compile check: pages/00_Landing_YTD.py")
try:
    compile(code_text, "pages/00_Landing_YTD.py", "exec")
    st.success("Compiled OK")
except Exception:
    st.error("Compile failed")
    st.code(traceback.format_exc())
