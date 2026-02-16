import streamlit as st

st.set_page_config(page_title="Cockpit", layout="wide")
st.title("Cockpit")
st.caption("Weekly operating view. Filters + KPIs + core drivers.")

with st.sidebar:
    st.header("Filters")
    st.selectbox("Location", ["All", "Brooklyn Digital", "Passaic Screen"], index=0)
    st.selectbox("Fiscal Year", ["FY2026"], index=0)
    st.slider("Week Range", 1, 52, (1, 8))

tab_weekly, tab_monthly, tab_ytd = st.tabs(["Weekly", "Monthly", "YTD vs Plan"])

with tab_weekly:
    st.subheader("Written / Produced / Invoiced")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Written", "—")
    c2.metric("Produced", "—")
    c3.metric("Invoiced", "—")
    c4.metric("Produced - Written", "—")
    st.info("Next: weekly trend chart + Produced minus Written bars, plus Digital vs Screen split.")

with tab_monthly:
    st.subheader("Monthly rollups (4-4-5)")
    st.info("Next: month view on your 4-4-5 calendar.")

with tab_ytd:
    st.subheader("YTD vs Plan / vs LY")
    st.info("Next: YTD actual vs plan, and YTD vs last year.")
