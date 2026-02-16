import streamlit as st

st.set_page_config(page_title="Executive Cockpit", layout="wide")

st.sidebar.success("Router running streamlit_app.py")

nav = st.navigation(
    {
        "Executive": [
            st.Page("pages/00_Landing_YTD.py", title="Landing - YTD"),
        ],
        "Operations": [
            st.Page("pages/01_Cockpit.py", title="Cockpit"),
            st.Page("pages/10_Home.py", title="Home"),
        ],
        "Admin": [
            st.Page("pages/90_Data.py", title="Data"),
            st.Page("pages/99_Debug.py", title="Debug"),
        ],
    }
)

nav.run()
