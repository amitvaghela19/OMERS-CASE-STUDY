"""Three management findings computed from the cleaned tables."""

from __future__ import annotations

import pandas as pd

from omers.metrics import (
    equity_regions,
    equity_steps,
    income_statement,
    kpi_amount,
    performance_returns,
    variance_pct,
)


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000_000:
        return f"{sign}${amount / 1_000_000_000:.2f}bn"
    if amount >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.2f}M"
    return f"{sign}${amount:,.0f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _signed_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.2f}%"


def build_findings(tables: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    hierarchy = tables["hierarchy"]
    kpis = tables["kpis"]
    balance = tables["bs_by_region"]
    equity = tables["equity_bridge"]
    asset_ids = set(hierarchy["asset_id"])
    returns = performance_returns(kpis, balance, asset_ids)
    statement = income_statement(kpis, asset_ids)
    return [
        _finding_return(returns, statement),
        _finding_watchlist(hierarchy, kpis, balance),
        _finding_equity(equity),
    ]


def _finding_return(returns: dict, statement: pd.DataFrame) -> dict[str, str]:
    if returns["forecast"] is None or returns["budget"] is None or statement.empty:
        return {
            "title": "Finding 1 — Forecast return",
            "observation": "Forecast and budget returns cannot be calculated from this file.",
            "implication": "Load a workbook with net income and equity before using this finding.",
            "evidence": "Portfolio performance. Performance return cards and the income statement.",
        }
    gap = returns["gap"] or 0.0
    direction = "below" if gap < 0 else "above"
    annual = statement[statement["Metric"] != "Total"].dropna(subset=["Annual Var"]).sort_values("Annual Var")
    leader = annual.iloc[0]
    lead_name = leader["Metric"]
    lead_var = float(leader["Annual Var"])
    total = statement[statement["Metric"] == "Total"].iloc[0]
    forecast_pct = _pct(returns["forecast"])
    budget_pct = _pct(returns["budget"])
    gap_pct = _signed_pct(gap)
    return {
        "title": f"Finding 1 — Forecast return is {abs(gap) * 100:.2f} points {direction} budget, led by {lead_name}",
        "observation": (
            f"Across the full portfolio, the forecast return is {forecast_pct} "
            f"and the budget return is {budget_pct} (variance {gap_pct}). "
            f"Annual forecast net income is {_money(returns['ni_forecast'])} vs annual budget "
            f"{_money(returns['ni_budget'])}. "
            f"The income statement total adds every line, including net income: "
            f"year to date {_money(float(total['YTD Actual']))} vs {_money(float(total['YTD Budget']))} "
            f"(YTD Var % {_signed_pct(float(total['YTD Var %']))}), and annual forecast "
            f"{_money(float(total['Annual Forecast']))} vs {_money(float(total['Annual Budget']))} "
            f"(Annual Var % {_signed_pct(float(total['Annual Var %']))}). "
            f"Each variance percent is the amount minus the budget, divided by the budget. "
            f"The largest annual dollar gap on a single line is {lead_name}: "
            f"{_money(float(leader['Annual Forecast']))} vs {_money(float(leader['Annual Budget']))} "
            f"({_signed_pct(leader['Annual Var %'])}, {_money(lead_var)})."
        ),
        "implication": (
            f"The return gap is led by {lead_name}. This line should be explained first when the full-year result is reviewed vs budget. "
            f"The total variance percents are calculated from the column totals."
            if lead_var < 0
            else f"{lead_name} is the widest annual dollar gap, and the variance is favorable. "
            f"The total variance percents are calculated from the column totals."
        ),
        "evidence": "Portfolio performance page: return cards, gauge, and income statement, with no slicer selected.",
    }


def _finding_watchlist(hierarchy: pd.DataFrame, kpis: pd.DataFrame, balance: pd.DataFrame) -> dict[str, str]:
    rows = []
    for asset in hierarchy.itertuples(index=False):
        ids = {asset.asset_id}
        ytd_actual = kpi_amount(kpis, ids, "Net Income", "YTD", "Actual")
        ytd_budget = kpi_amount(kpis, ids, "Net Income", "YTD", "Budget")
        annual_forecast = kpi_amount(kpis, ids, "Net Income", "Annual", "Forecast")
        annual_budget = kpi_amount(kpis, ids, "Net Income", "Annual", "Budget")
        ytd_var = ytd_actual - ytd_budget
        annual_var = annual_forecast - annual_budget
        if ytd_var < 0 and annual_var < 0:
            stats = performance_returns(kpis, balance, ids)
            rows.append(
                f"{asset.asset_id} ({asset.country}, {asset.sector}), year to date {_money(ytd_actual)} vs "
                f"{_money(ytd_budget)} ({_signed_pct(variance_pct(ytd_actual, ytd_budget))}), and annual forecast "
                f"{_money(annual_forecast)} vs {_money(annual_budget)} "
                f"({_signed_pct(variance_pct(annual_forecast, annual_budget))})"
                + (
                    f"; forecast return {_pct(stats['forecast'])}"
                    if stats["forecast"] is not None
                    else ""
                )
            )
    if not rows:
        observation = "No asset is behind budget on both the year-to-date result and the annual forecast."
        implication = "This file does not produce a two-view watchlist."
    else:
        observation = (
            "Net income is behind budget on both the year-to-date result and the annual forecast for "
            + "; ".join(rows)
            + "."
        )
        implication = "These assets form the watchlist and should be reviewed in order of the dollar gap."
    return {
        "title": "Finding 2 — Assets behind on both YTD and the annual forecast",
        "observation": observation,
        "implication": implication,
        "evidence": "Income statement details for each asset, and the forecast-return bar on Portfolio performance.",
    }


def _finding_equity(equity: pd.DataFrame) -> dict[str, str]:
    scenario = "December 2019"
    steps = equity_steps(equity, scenario)
    if steps.empty:
        return {
            "title": "Finding 3 — Equity movement",
            "observation": "December 2019 is not in this file.",
            "implication": "Select the year-end scenario that is available before commenting on equity movement.",
            "evidence": "Equity movements page. Equity bridge waterfall.",
        }
    opening = float(steps.loc[steps["category"] == "Opening", "value"].iloc[0])
    total = float(steps.loc[steps["category"] == "Total", "value"].iloc[0])
    changes = steps[steps["kind"] == "change"]
    up = changes.sort_values("value", ascending=False).iloc[0]
    down = changes.sort_values("value", ascending=True).iloc[0]
    regions = equity_regions(equity, scenario)
    region_text = "; ".join(
        f"{row.region} {_money(row.total)} from an opening of {_money(row.opening)}"
        for row in regions.itertuples(index=False)
    )
    debt = changes[changes["category"] == "Debt MTM"]
    debt_text = _money(float(debt["value"].iloc[0])) if not debt.empty else "not in the bridge"
    return {
        "title": f"Finding 3 — December equity moves from {_money(opening)} to {_money(total)}",
        "observation": (
            f"With December 2019 selected and no region selected, opening equity is {_money(opening)} "
            f"and the total is {_money(total)}. The largest increase is {up.category} {_money(float(up.value))}. "
            f"The largest decrease is {down.category} {_money(float(down.value))}. By region: {region_text}."
        ),
        "implication": (
            f"Year-end equity movement is led by {up.category}, partly offset by {down.category}. "
            f"Debt mark-to-market is {debt_text}."
        ),
        "evidence": "Equity movements page. Scenario set to December 2019 and no region selected, then each region on its own.",
    }
