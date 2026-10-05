import pandas as pd
import streamlit as st

from omers.store import preview_table, recent_log, run_select, table_schema

EXAMPLES = {
    "Write your own": "",
    "Net income by asset": (
        "SELECT asset_id, time_view, scenario, amount\n"
        "FROM kpis\n"
        "WHERE metric = 'Net Income'\n"
        "ORDER BY asset_id, time_view, scenario"
    ),
    "Balance sheet by scenario": (
        "SELECT asset_id, category, scenario, amount\n"
        "FROM bs_by_region\n"
        "ORDER BY asset_id, category_sort, scenario_sort"
    ),
    "December 2019 equity bridge": (
        "SELECT region, attribution_category, bridge\n"
        "FROM equity_bridge\n"
        "WHERE scenario = 'December 2019'\n"
        "ORDER BY region, sort_order"
    ),
}

NOTES = {
    "hierarchy": "One row per asset: region, country, and sector.",
    "bs_by_region": "Balance-sheet amounts. Scenarios are YTD Actual, Annual Forecast, and Annual Budget.",
    "kpis": "Income-statement lines. time_view is YTD or Annual. scenario is Actual, Budget, or Forecast.",
    "equity_bridge": "Equity movement by region. scenario is January, June, or December 2019.",
}

st.header("SQL")
st.caption("Read-only. One SELECT against hierarchy, bs_by_region, kpis, or equity_bridge.")

if not st.session_state.get("loaded"):
    st.warning("Upload a workbook in the sidebar to load the database.")
    st.stop()

if "sql_query" not in st.session_state:
    st.session_state.sql_query = EXAMPLES["Net income by asset"]
if "sql_example_pick" not in st.session_state:
    st.session_state.sql_example_pick = "Net income by asset"


def _use_table(name: str) -> None:
    columns = next(item["columns"] for item in table_schema() if item["name"] == name)
    names = ", ".join(column for column, _typ in columns)
    st.session_state.sql_query = f"SELECT {names}\nFROM {name}\nLIMIT 100"


def _insert_column(table: str, column: str) -> None:
    token = f"{table}.{column}"
    current = st.session_state.get("sql_query", "").rstrip()
    if not current:
        st.session_state.sql_query = f"SELECT {token}\nFROM {table}"
        return
    joiner = "\n" if current.endswith((";", ")")) else " "
    st.session_state.sql_query = current + joiner + token


def _load_saved(sql_text: str) -> None:
    st.session_state.sql_query = sql_text
    st.session_state.sql_example_pick = "Write your own"


def _apply_example() -> None:
    picked = st.session_state.sql_example_pick
    if EXAMPLES.get(picked):
        st.session_state.sql_query = EXAMPLES[picked]


def _clear_query() -> None:
    st.session_state.sql_query = ""
    st.session_state.sql_example_pick = "Write your own"
    st.session_state.sql_result = None
    st.session_state.sql_error = ""


def _column_label(column: str) -> str:
    return column[:1].upper() + column[1:]


schema = table_schema()

catalog, work = st.columns([1, 2.1], gap="large")

with catalog:
    st.subheader("Tables")
    st.caption("Open a table, then add a column to the query.")
    st.markdown(
        """
        <style>
        div[data-testid="stElementContainer"]:has(.sql-start) {
            display: none;
        }
        div[data-testid="stElementContainer"]:has(.sql-start)
            + div[data-testid="stElementContainer"] button {
            background-color: #D6EBFA;
            border: 1px solid #7EB6E0;
            color: #0B3A5B;
        }
        div[data-testid="stElementContainer"]:has(.sql-start)
            + div[data-testid="stElementContainer"] button:hover {
            background-color: #C5E0F5;
            border-color: #5AA3D6;
            color: #0B3A5B;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for item in schema:
        name = str(item["name"])
        columns = item["columns"]
        column_count = len(columns)
        column_word = "column" if column_count == 1 else "columns"
        with st.expander(
            f"{name}  ·  {item['rows']} rows  ·  {column_count} {column_word}",
            expanded=name == "kpis",
        ):
            st.caption(NOTES[name])
            st.markdown('<div class="sql-start"></div>', unsafe_allow_html=True)
            st.button(
                "Start a query",
                key=f"use_{name}",
                width="stretch",
                on_click=_use_table,
                args=(name,),
            )
            for column, _typ in columns:
                st.button(
                    _column_label(column),
                    key=f"col_{name}_{column}",
                    width="stretch",
                    on_click=_insert_column,
                    args=(name, column),
                )
            if st.checkbox("Preview 5 rows", key=f"preview_{name}"):
                st.dataframe(preview_table(name), width="stretch", hide_index=True, height=180)

with work:
    st.subheader("Query")
    st.selectbox(
        "Start from an example",
        list(EXAMPLES),
        key="sql_example_pick",
        on_change=_apply_example,
    )
    log = recent_log()
    saved = log[log["status"] == "ok"]["sql_text"].drop_duplicates().tolist() if not log.empty else []
    if saved:
        chosen = st.selectbox("Or reopen a recent query", ["Keep current query", *saved])
        st.button(
            "Load into editor",
            disabled=chosen == "Keep current query",
            on_click=_load_saved,
            args=(chosen,),
        )
    query = st.text_area("Query", key="sql_query", height=220, placeholder="SELECT ...")
    run_col, clear_col = st.columns(2)
    run = run_col.button("Run query", type="primary", width="stretch")
    clear_col.button("Clear", width="stretch", on_click=_clear_query)
    if run:
        try:
            result = run_select(query, source="sql_tab")
        except Exception as exc:
            st.session_state.sql_result = None
            st.session_state.sql_error = str(exc)
        else:
            st.session_state.sql_result = result
            st.session_state.sql_error = ""
    error = st.session_state.get("sql_error") or ""
    result = st.session_state.get("sql_result")
    if error:
        st.error(error)
    elif isinstance(result, pd.DataFrame):
        st.caption(f"{len(result)} rows")
        st.dataframe(result, width="stretch", hide_index=True)
        st.download_button(
            "Download CSV",
            result.to_csv(index=False).encode("utf-8"),
            file_name="query.csv",
            mime="text/csv",
            width="content",
        )

st.subheader("Query log")
if log.empty:
    st.caption("No queries have been logged yet.")
else:
    st.dataframe(log, width="stretch", hide_index=True)
