"""Portfolio measures used by the three dashboard pages."""

from __future__ import annotations

import pandas as pd

SCENARIO_ORDER = ["YTD Actual", "Annual Forecast", "Annual Budget"]
AUM_CATEGORIES = ["Equity", "Debt", "3rd Party"]
KPI_VIEWS = (
    ("YTD Actual", "YTD", "Actual"),
    ("YTD Budget", "YTD", "Budget"),
    ("Annual Budget", "Annual", "Budget"),
    ("Annual Forecast", "Annual", "Forecast"),
)


def filter_assets(
    hierarchy: pd.DataFrame,
    regions: list[str] | None = None,
    countries: list[str] | None = None,
    sectors: list[str] | None = None,
    assets: list[str] | None = None,
) -> pd.DataFrame:
    out = hierarchy.copy()
    if regions:
        out = out[out["region"].isin(regions)]
    if countries:
        out = out[out["country"].isin(countries)]
    if sectors:
        out = out[out["sector"].isin(sectors)]
    if assets:
        out = out[out["asset_id"].isin(assets)]
    return out


def _scoped(frame: pd.DataFrame, asset_ids: set[str]) -> pd.DataFrame:
    return frame[frame["asset_id"].isin(asset_ids)].copy()


def kpi_amount(kpis: pd.DataFrame, asset_ids: set[str], metric: str, time_view: str, scenario: str) -> float:
    rows = kpis[
        kpis["asset_id"].isin(asset_ids)
        & (kpis["metric"] == metric)
        & (kpis["time_view"] == time_view)
        & (kpis["scenario"] == scenario)
    ]
    return float(rows["amount"].sum())


def bs_amount(balance: pd.DataFrame, asset_ids: set[str], category: str, scenario: str) -> float:
    rows = balance[
        balance["asset_id"].isin(asset_ids)
        & (balance["category"] == category)
        & (balance["scenario"] == scenario)
    ]
    return float(rows["amount"].sum())


def variance_pct(actual: float, budget: float) -> float:
    """(actual − budget) / budget, or (forecast − budget) / budget. A zero budget is 0%."""
    if budget == 0:
        return 0.0
    return (actual - budget) / budget


def performance_returns(kpis: pd.DataFrame, balance: pd.DataFrame, asset_ids: set[str]) -> dict[str, float | None]:
    ni_forecast = kpi_amount(kpis, asset_ids, "Net Income", "Annual", "Forecast")
    ni_budget = kpi_amount(kpis, asset_ids, "Net Income", "Annual", "Budget")
    equity_forecast = bs_amount(balance, asset_ids, "Equity", "Annual Forecast")
    equity_budget = bs_amount(balance, asset_ids, "Equity", "Annual Budget")
    forecast = ni_forecast / equity_forecast if equity_forecast else None
    budget = ni_budget / equity_budget if equity_budget else None
    gap = None if forecast is None or budget is None else forecast - budget
    return {
        "ni_forecast": ni_forecast,
        "ni_budget": ni_budget,
        "equity_forecast": equity_forecast,
        "equity_budget": equity_budget,
        "forecast": forecast,
        "budget": budget,
        "gap": gap,
    }


def income_statement(kpis: pd.DataFrame, asset_ids: set[str]) -> pd.DataFrame:
    scoped = _scoped(kpis, asset_ids)
    if scoped.empty:
        return pd.DataFrame()
    rows = []
    metrics = (
        scoped[["metric", "metric_sort"]]
        .drop_duplicates()
        .sort_values("metric_sort")
    )
    for metric, _sort in metrics.itertuples(index=False):
        values = {}
        for label, time_view, scenario in KPI_VIEWS:
            part = scoped[
                (scoped["metric"] == metric)
                & (scoped["time_view"] == time_view)
                & (scoped["scenario"] == scenario)
            ]
            values[label] = float(part["amount"].sum())
        values["YTD Var"] = values["YTD Actual"] - values["YTD Budget"]
        values["Annual Var"] = values["Annual Forecast"] - values["Annual Budget"]
        values["YTD Var %"] = variance_pct(values["YTD Actual"], values["YTD Budget"])
        values["Annual Var %"] = variance_pct(values["Annual Forecast"], values["Annual Budget"])
        values["Metric"] = metric
        rows.append(values)
    frame = pd.DataFrame(rows)
    numeric = [column for column in frame.columns if column != "Metric"]
    total = {column: float(frame[column].sum()) for column in numeric}
    total["YTD Var %"] = variance_pct(total["YTD Actual"], total["YTD Budget"])
    total["Annual Var %"] = variance_pct(total["Annual Forecast"], total["Annual Budget"])
    total["Metric"] = "Total"
    return pd.concat([frame, pd.DataFrame([total])], ignore_index=True)


def aum_by_scenario(balance: pd.DataFrame, asset_ids: set[str]) -> pd.DataFrame:
    scoped = _scoped(balance, asset_ids)
    scoped = scoped[scoped["category"].isin(AUM_CATEGORIES)]
    grouped = (
        scoped.groupby(["scenario", "scenario_sort", "category"], as_index=False)["amount"]
        .sum()
    )
    return grouped.sort_values(["scenario_sort", "category"])


def sector_mix(balance: pd.DataFrame, hierarchy: pd.DataFrame, asset_ids: set[str]) -> pd.DataFrame:
    scoped = _scoped(balance, asset_ids)
    gav = scoped[scoped["category"] == "Real Estate"].merge(
        hierarchy[["asset_id", "sector"]], on="asset_id", how="left"
    )
    grouped = gav.groupby(["scenario", "scenario_sort", "sector"], as_index=False)["amount"].sum()
    totals = grouped.groupby("scenario")["amount"].transform("sum")
    grouped["share"] = grouped["amount"] / totals.replace(0, pd.NA)
    return grouped.sort_values(["scenario_sort", "sector"])


def return_by_asset(kpis: pd.DataFrame, balance: pd.DataFrame, hierarchy: pd.DataFrame, asset_ids: set[str]) -> pd.DataFrame:
    rows = []
    for asset_id in sorted(asset_ids):
        stats = performance_returns(kpis, balance, {asset_id})
        info = hierarchy[hierarchy["asset_id"] == asset_id]
        rows.append(
            {
                "asset_id": asset_id,
                "region": info["region"].iloc[0] if not info.empty else "",
                "country": info["country"].iloc[0] if not info.empty else "",
                "sector": info["sector"].iloc[0] if not info.empty else "",
                "forecast_return": stats["forecast"],
                "budget_return": stats["budget"],
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("forecast_return", ascending=False, na_position="last")


def noi_vs_mtm(kpis: pd.DataFrame, asset_ids: set[str]) -> pd.DataFrame:
    rows = []
    for asset_id in sorted(asset_ids):
        ids = {asset_id}
        rows.append(
            {
                "asset_id": asset_id,
                "NOI": kpi_amount(kpis, ids, "NOI", "YTD", "Actual"),
                "MTM Assets": kpi_amount(kpis, ids, "MTM Assets", "YTD", "Actual"),
                "MTM Debt": kpi_amount(kpis, ids, "MTM Debt", "YTD", "Actual"),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.melt(id_vars="asset_id", var_name="line", value_name="amount")


def equity_steps(equity: pd.DataFrame, scenario: str, regions: list[str] | None = None) -> pd.DataFrame:
    scoped = equity[equity["scenario"] == scenario].copy()
    if regions:
        scoped = scoped[scoped["region"].isin(regions)]
    if scoped.empty:
        return pd.DataFrame()
    grouped = (
        scoped.groupby(["attribution_category", "sort_order"], as_index=False)["bridge"]
        .sum()
        .sort_values("sort_order")
    )
    steps = []
    running = 0.0
    for row in grouped.itertuples(index=False):
        value = float(row.bridge)
        kind = "opening" if row.attribution_category == "Opening" else "change"
        if kind == "change":
            start, end = running, running + value
        else:
            start, end = 0.0, value
        steps.append(
            {
                "category": row.attribution_category,
                "value": value,
                "start": start,
                "end": end,
                "kind": kind,
            }
        )
        running += value
    steps.append(
        {
            "category": "Total",
            "value": running,
            "start": 0.0,
            "end": running,
            "kind": "total",
        }
    )
    return pd.DataFrame(steps)


def equity_regions(equity: pd.DataFrame, scenario: str) -> pd.DataFrame:
    scoped = equity[equity["scenario"] == scenario]
    totals = scoped.groupby("region", as_index=False)["bridge"].sum().rename(columns={"bridge": "total"})
    opening = (
        scoped[scoped["attribution_category"] == "Opening"]
        .groupby("region", as_index=False)["bridge"]
        .sum()
        .rename(columns={"bridge": "opening"})
    )
    return opening.merge(totals, on="region", how="outer").fillna(0.0)
