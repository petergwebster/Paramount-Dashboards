import streamlit as st

st.set_page_config(page_title="Paramount Dashboard", layout="wide")

st.title("Paramount Weekly Dashboard")
st.caption("Brooklyn Digital + Passaic Screen | 4-4-5 Calendar | KPIs in yards")

st.markdown(
    """
#### How to use this app
This landing page is the *story view*.
Use **Cockpit** for the weekly operating view, then drill into Ops/Production and Waste when you need detail.
"""
)

kpi_a, kpi_b, kpi_c, kpi_d = st.columns(4)
kpi_a.metric("Written (latest)", "—")
kpi_b.metric("Produced (latest)", "—")
kpi_c.metric("Invoiced (latest)", "—")
kpi_d.metric("Produced / Written", "—")

st.markdown("#### Weekly trend")
st.info("Next: we’ll wire this to your Written/Produced/Invoiced weekly tables and add the main trend chart + gap chart.")
