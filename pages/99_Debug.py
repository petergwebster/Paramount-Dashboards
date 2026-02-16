import traceback

st.subheader("Compile check: pages/00_Landing_YTD.py")

try:
    code_text = Path("pages/00_Landing_YTD.py").read_text(errors="ignore")
    compile(code_text, "pages/00_Landing_YTD.py", "exec")
    st.success("Compiled OK")
except Exception as e:
    st.error("Compile failed")
    st.code(traceback.format_exc())
