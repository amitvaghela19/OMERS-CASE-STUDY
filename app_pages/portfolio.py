import streamlit as st

from omers.metrics import (
    aum_by_scenario,
    filter_assets,
    income_statement,
    noi_vs_mtm,
    performance_returns,
    return_by_asset,
    sector_mix,
)
from omers.present import aum_chart, gauge, millions, mtm_chart, return_chart, sector_chart, variance_card
from omers.store import load_tables

def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


st.header("Portfolio performance")
st.caption("Case-study data. Positive variance is green and negative variance is red.")

if not st.session_state.get("loaded"):
    st.warning("Upload a workbook in the sidebar to load the dashboard.")
    st.stop()

tables = load_tables()
hierarchy = tables["hierarchy"]
if st.button("Reset cohort", icon=":material/filter_alt_off:"):
    st.session_state.cohort_region = []
    st.session_state.cohort_country = []
    st.session_state.cohort_sector = []
    st.session_state.cohort_asset = []
st.markdown(
    """
    <style>
    div[data-testid="stVerticalBlock"]:has(.cohort-slicers) [data-testid="stButtonGroup"] > div {
        flex-wrap: wrap !important;
        overflow: visible !important;
        height: auto !important;
    }
    </style>
    <span class="cohort-slicers"></span>
    """,
    unsafe_allow_html=True,
)
region_col, country_col = st.columns(2)
sector_col, asset_col = st.columns(2)
regions = region_col.pills(
    "Region",
    sorted(hierarchy["region"].unique()),
    selection_mode="multi",
    key="cohort_region",
    default=[],
)
countries = country_col.pills(
    "Country",
    sorted(hierarchy["country"].unique()),
    selection_mode="multi",
    key="cohort_country",
    default=[],
)
sectors = sector_col.pills(
    "Sector",
    sorted(hierarchy["sector"].unique()),
    selection_mode="multi",
    key="cohort_sector",
    default=[],
)
assets = asset_col.pills(
    "Asset",
    sorted(hierarchy["asset_id"].unique()),
    selection_mode="multi",
    key="cohort_asset",
    default=[],
)
chosen = filter_assets(hierarchy, regions, countries, sectors, assets)
asset_ids = set(chosen["asset_id"])

if not asset_ids:
    st.info("No assets match these filters.")
    st.stop()

stats = performance_returns(tables["kpis"], tables["bs_by_region"], asset_ids)
left, mid, right = st.columns(3, border=True)
left.metric("Forecast return", _pct(stats["forecast"]))
mid.metric("Budget return", _pct(stats["budget"]))
gap = None if stats["gap"] is None else stats["gap"] * 100
variance_card(right, gap)
_, gauge_col, _ = st.columns([1, 2, 1])
gauge_col.altair_chart(gauge(stats["forecast"], stats["budget"]), width="content")

statement = income_statement(tables["kpis"], asset_ids)
st.subheader("Income statement")
st.caption(
    "Figures in $ millions. YTD variance percent is (YTD actual − YTD budget) / YTD budget. "
    "Annual variance percent is (annual forecast − annual budget) / annual budget. "
    "A zero budget is 0%."
)
st.dataframe(millions(statement), width="stretch", height="content", hide_index=True)

chart_left, chart_right = st.columns([1, 1.35])
with chart_left:
    st.subheader("AUM = Equity + Debt + 3rd Party")
    st.altair_chart(aum_chart(aum_by_scenario(tables["bs_by_region"], asset_ids)), width="stretch")
with chart_right:
    st.subheader("Real Estate Value Mix by Sector")
    st.altair_chart(
        sector_chart(sector_mix(tables["bs_by_region"], hierarchy, asset_ids)),
        width="stretch",
    )

bar_left, bar_right = st.columns(2)
with bar_left:
    st.subheader("Performance Return by Asset, Forecast")
    st.altair_chart(
        return_chart(return_by_asset(tables["kpis"], tables["bs_by_region"], hierarchy, asset_ids)),
        width="stretch",
    )
with bar_right:
    st.subheader("NOI vs Mark-to-Market, YTD")
    st.altair_chart(mtm_chart(noi_vs_mtm(tables["kpis"], asset_ids)), width="stretch")
