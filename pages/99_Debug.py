import os
import streamlit as st

st.set_page_config(page_title="Debug", layout="wide")

st.title("Debug")
st.write("cwd")
st.write(os.getcwd())

st.write("root files")
st.write(sorted(os.listdir(".")))

st.write("pages files")
st.write(sorted(os.listdir("pages")))
