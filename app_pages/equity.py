import streamlit as st

from omers.metrics import equity_steps
from omers.present import waterfall_chart
from omers.store import load_tables

st.header("Equity movements")
st.caption("One scenario at a time, so opening balances are not added across January, June, and December.")

if not st.session_state.get("loaded"):
    st.warning("Upload a workbook in the sidebar to load the dashboard.")
    st.stop()

equity = load_tables()["equity_bridge"]
scenarios = (
    equity[["scenario", "scenario_sort"]]
    .drop_duplicates()
    .sort_values("scenario_sort")["scenario"]
    .tolist()
)
default_scenario = "December 2019" if "December 2019" in scenarios else scenarios[0]
regions = ["All", *sorted(equity["region"].unique())]
if st.button("Reset cohort", icon=":material/filter_alt_off:"):
    st.session_state.equity_region = "All"
    st.session_state.equity_scenario = default_scenario
picked_region = st.pills("Region", regions, selection_mode="single", default="All", key="equity_region")
picked_scenario = st.pills(
    "Scenario",
    scenarios,
    selection_mode="single",
    default=default_scenario,
    key="equity_scenario",
)
region_filter = None if picked_region in (None, "All") else [picked_region]
scenario = picked_scenario or default_scenario
steps = equity_steps(equity, scenario, region_filter)
if steps.empty:
    st.info("No equity bridge rows match this selection.")
    st.stop()

st.subheader(f"Equity bridge, {scenario}")
st.altair_chart(waterfall_chart(steps), width="stretch")
show = steps.copy()
show["Amount"] = show["value"].map(lambda v: f"${v / 1_000_000_000:.2f}bn")
st.dataframe(show[["category", "Amount"]], width="stretch", hide_index=True)
