"""Clean a case-study workbook into the four dashboard tables."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

REQUIRED_SHEETS = ("Hierarchy", "BS by Region", "KPI's", "Equity Bridge")

METRIC_SORT = {
    "NOI": 1,
    "Interest": 2,
    "Net G&A": 3,
    "FF&E Amort": 4,
    "Recoverable Capital Amort": 5,
    "Current Income Tax": 6,
    "Current Capital Tax": 7,
    "MTM Assets": 8,
    "MTM Debt": 9,
    "Other Gain / Loss": 10,
    "Net Income": 11,
}

CATEGORY_SORT = {"Equity": 1, "Debt": 2, "Real Estate": 3, "3rd Party": 4}

BS_SCENARIO = {
    "YTD Actual": ("YTD Actual", 1),
    "Forecast": ("Annual Forecast", 2),
    "Annual Forecast": ("Annual Forecast", 2),
    "Operating Plan": ("Annual Budget", 3),
    "Annual Budget": ("Annual Budget", 3),
}

EQUITY_SCENARIO = {
    "jan 2019": ("January 2019", 1),
    "january 2019": ("January 2019", 1),
    "jun 2019": ("June 2019", 2),
    "june 2019": ("June 2019", 2),
    "dec 2019": ("December 2019", 3),
    "december 2019": ("December 2019", 3),
}

KPI_SUFFIXES = (
    ("-YTD Variance", "YTD", "Variance"),
    ("-YTD Budget", "YTD", "Budget"),
    ("-Forecast", "Annual", "Forecast"),
    ("-Budget", "Annual", "Budget"),
    ("-Variance", "Annual", "Variance"),
    ("-Actual", "YTD", "Actual"),
)


def clean_workbook(source: str | Path | BytesIO) -> tuple[dict[str, pd.DataFrame], list[str]]:
    excel = pd.ExcelFile(source)
    missing = [name for name in REQUIRED_SHEETS if name not in excel.sheet_names]
    if missing:
        raise ValueError(
            "This workbook is missing required sheets: " + ", ".join(missing) + "."
        )
    notes = [
        "Loaded sheets: " + ", ".join(REQUIRED_SHEETS) + ".",
        "Instructions, Returns, and Sheet1 are not used.",
    ]
    hierarchy = _clean_hierarchy(pd.read_excel(excel, "Hierarchy"))
    balance = _clean_balance(pd.read_excel(excel, "BS by Region"))
    kpis = _clean_kpis(pd.read_excel(excel, "KPI's", header=None))
    equity = _clean_equity(pd.read_excel(excel, "Equity Bridge"))
    notes.append(f"Hierarchy rows: {len(hierarchy)}.")
    notes.append(f"Balance-sheet rows: {len(balance)}.")
    notes.append(f"Income-statement rows: {len(kpis)}.")
    notes.append(f"Equity-bridge rows: {len(equity)}.")
    frames = {
        "hierarchy": hierarchy,
        "bs_by_region": balance,
        "kpis": kpis,
        "equity_bridge": equity,
    }
    return frames, notes


def _headers(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.columns = [str(col).strip() for col in out.columns]
    return out


def _require(frame: pd.DataFrame, columns: list[str], sheet: str) -> None:
    missing = [col for col in columns if col not in frame.columns]
    if missing:
        raise ValueError(sheet + " is missing columns: " + ", ".join(missing) + ".")


def _clean_hierarchy(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _headers(frame)
    _require(frame, ["Region", "Country", "Sector", "Asset ID"], "Hierarchy")
    out = frame[["Region", "Country", "Sector", "Asset ID"]].copy()
    for col in out.columns:
        out[col] = out[col].map(lambda v: "" if pd.isna(v) else str(v).strip())
    out = out[out["Asset ID"] != ""]
    out = out.drop_duplicates(subset=["Asset ID"])
    return out.rename(
        columns={
            "Region": "region",
            "Country": "country",
            "Sector": "sector",
            "Asset ID": "asset_id",
        }
    )


def _clean_balance(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _headers(frame)
    _require(
        frame,
        ["Category", "Asset ID", "YTD Actual", "Forecast", "Operating Plan"],
        "BS by Region",
    )
    out = frame[frame["Category"].notna()].copy()
    out["Category"] = out["Category"].map(lambda v: str(v).strip())
    out = out[out["Category"] != "AUM"]
    out["Asset ID"] = out["Asset ID"].map(lambda v: "" if pd.isna(v) else str(v).strip())
    out = out[out["Asset ID"] != ""]
    if "Category Sort" in out.columns:
        out["Category Sort"] = pd.to_numeric(out["Category Sort"], errors="coerce")
    else:
        out["Category Sort"] = pd.NA
    out["Category Sort"] = out["Category Sort"].fillna(
        out["Category"].map(CATEGORY_SORT)
    )
    for col in ("YTD Actual", "Forecast", "Operating Plan"):
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).round(2)
    grouped = (
        out.groupby(["Asset ID", "Category", "Category Sort"], as_index=False)[
            ["YTD Actual", "Forecast", "Operating Plan"]
        ]
        .sum()
    )
    long = grouped.melt(
        id_vars=["Asset ID", "Category", "Category Sort"],
        value_vars=["YTD Actual", "Forecast", "Operating Plan"],
        var_name="scenario_raw",
        value_name="amount",
    )
    mapped = long["scenario_raw"].map(lambda v: BS_SCENARIO.get(str(v), (str(v), 9)))
    long["scenario"] = mapped.map(lambda v: v[0])
    long["scenario_sort"] = mapped.map(lambda v: v[1])
    return long.rename(
        columns={
            "Asset ID": "asset_id",
            "Category": "category",
            "Category Sort": "category_sort",
        }
    )[
        [
            "asset_id",
            "category",
            "category_sort",
            "scenario",
            "scenario_sort",
            "amount",
        ]
    ]


def _kpi_header_row(raw: pd.DataFrame) -> int:
    for index, row in raw.iterrows():
        values = ["" if pd.isna(v) else str(v).strip() for v in row.tolist()]
        if "Asset ID" in values and any(v.startswith("NOI") or v == "Description" for v in values):
            return int(index)
    raise ValueError("KPI's is missing the Asset ID header row.")


def _parse_kpi_attribute(name: str) -> tuple[str, str, str] | None:
    for suffix, time_view, scenario in KPI_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)], time_view, scenario
    return None


def _clean_kpis(raw: pd.DataFrame) -> pd.DataFrame:
    header = _kpi_header_row(raw)
    frame = raw.iloc[header + 1 :].copy()
    frame.columns = ["" if pd.isna(v) else str(v).strip() for v in raw.iloc[header].tolist()]
    frame = frame.loc[:, [col for col in frame.columns if col]]
    _require(frame, ["Asset ID"], "KPI's")
    if "Description" in frame.columns:
        frame = frame.drop(columns=["Description"])
    frame["Asset ID"] = frame["Asset ID"].map(lambda v: "" if pd.isna(v) else str(v).strip())
    frame = frame[frame["Asset ID"] != ""]
    value_cols = [col for col in frame.columns if col != "Asset ID"]
    for col in value_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
    grouped = frame.groupby("Asset ID", as_index=False)[value_cols].sum()
    long = grouped.melt(id_vars=["Asset ID"], var_name="attribute", value_name="amount")
    parsed = long["attribute"].map(_parse_kpi_attribute)
    long = long[parsed.notna()].copy()
    parsed = parsed[parsed.notna()]
    long["metric"] = parsed.map(lambda v: v[0])
    long["time_view"] = parsed.map(lambda v: v[1])
    long["scenario"] = parsed.map(lambda v: v[2])
    long = long[long["scenario"] != "Variance"]
    long["metric_sort"] = long["metric"].map(lambda v: METRIC_SORT.get(v, 99))
    out = long.rename(columns={"Asset ID": "asset_id"})
    out = (
        out.groupby(
            ["asset_id", "metric", "metric_sort", "time_view", "scenario"],
            as_index=False,
        )["amount"]
        .sum()
    )
    return out[
        ["asset_id", "metric", "metric_sort", "time_view", "scenario", "amount"]
    ]


def _clean_equity(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _headers(frame)
    _require(
        frame,
        ["Region", "Scenario", "Attribution Category", "Bridge"],
        "Equity Bridge",
    )
    out = frame.copy()
    for col in ("Region", "Scenario", "Attribution Category"):
        out[col] = out[col].map(lambda v: "" if pd.isna(v) else str(v).strip())
    out = out[(out["Region"] != "") & (out["Attribution Category"] != "")]
    mapped = out["Scenario"].map(
        lambda v: EQUITY_SCENARIO.get(v.lower(), (v, 9))
    )
    out["scenario"] = mapped.map(lambda v: v[0])
    out["scenario_sort"] = mapped.map(lambda v: v[1])
    out["bridge"] = pd.to_numeric(out["Bridge"], errors="coerce").fillna(0.0)
    if "Annual Impact" in out.columns:
        out["annual_impact"] = pd.to_numeric(out["Annual Impact"], errors="coerce")
    else:
        out["annual_impact"] = pd.NA
    if "Sort Order" in out.columns:
        out["sort_order"] = pd.to_numeric(out["Sort Order"], errors="coerce").fillna(99)
    else:
        out["sort_order"] = 99
    out = out.rename(
        columns={"Region": "region", "Attribution Category": "attribution_category"}
    )
    grouped = out.groupby(
        ["region", "scenario", "scenario_sort", "attribution_category", "sort_order"],
        as_index=False,
    ).agg(bridge=("bridge", "sum"), annual_impact=("annual_impact", "sum"))
    return grouped.sort_values(["scenario_sort", "region", "sort_order"])
