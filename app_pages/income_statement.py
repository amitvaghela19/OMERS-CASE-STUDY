import streamlit as st

from omers.metrics import filter_assets, income_statement, performance_returns
from omers.present import millions, variance_card
from omers.store import load_tables

def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


st.header("Income statement details")
st.caption("Same income statement as the portfolio page, for one asset.")

if not st.session_state.get("loaded"):
    st.warning("Upload a workbook in the sidebar to load the dashboard.")
    st.stop()

tables = load_tables()
hierarchy = tables["hierarchy"]
regions = st.pills("Region", sorted(hierarchy["region"].unique()), selection_mode="multi", key="is_region")
countries = st.pills("Country", sorted(hierarchy["country"].unique()), selection_mode="multi", key="is_country")
sectors = st.pills("Sector", sorted(hierarchy["sector"].unique()), selection_mode="multi", key="is_sector")
chosen = filter_assets(hierarchy, regions, countries, sectors)
if chosen.empty:
    st.info("No assets match these filters.")
    st.stop()

asset = st.selectbox("Asset", chosen["asset_id"].tolist())
info = chosen[chosen["asset_id"] == asset].iloc[0]
c1, c2, c3 = st.columns(3, border=True)
c1.metric("Region", info["region"])
c2.metric("Country", info["country"])
c3.metric("Sector", info["sector"])

stats = performance_returns(tables["kpis"], tables["bs_by_region"], {asset})
r1, r2, r3 = st.columns(3, border=True)
r1.metric("Forecast return", _pct(stats["forecast"]))
r2.metric("Budget return", _pct(stats["budget"]))
gap = None if stats["gap"] is None else stats["gap"] * 100
variance_card(r3, gap)

st.subheader("Income statement, all lines")
st.caption("Figures in $ millions.")
st.dataframe(
    millions(income_statement(tables["kpis"], {asset})),
    width="stretch",
    height="content",
    hide_index=True,
)
