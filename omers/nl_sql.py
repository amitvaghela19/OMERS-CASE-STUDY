"""Turn a natural-language question into one read-only statement with temporary CTEs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from omers.metrics import variance_pct

REFUSAL = "I don't know the answer, but I will get back to you."

METRIC_ALIASES = (
    ("recoverable capital amort", "Recoverable Capital Amort"),
    ("recoverable capital", "Recoverable Capital Amort"),
    ("other gain / loss", "Other Gain / Loss"),
    ("other gain/loss", "Other Gain / Loss"),
    ("other gains", "Other Gain / Loss"),
    ("other gain", "Other Gain / Loss"),
    ("current income tax", "Current Income Tax"),
    ("income tax", "Current Income Tax"),
    ("current capital tax", "Current Capital Tax"),
    ("capital tax", "Current Capital Tax"),
    ("mtm real estate", "MTM Assets"),
    ("mtm assets", "MTM Assets"),
    ("mtm debt", "MTM Debt"),
    ("net g&a", "Net G&A"),
    ("net g and a", "Net G&A"),
    ("g&a", "Net G&A"),
    ("ff&e amort", "FF&E Amort"),
    ("ff&e", "FF&E Amort"),
    ("net income", "Net Income"),
    ("bottom line", "Net Income"),
    ("interest", "Interest"),
    ("noi", "NOI"),
)
EQUITY_ALIASES = (
    ("other capital contributions", "Other Capital Contributions"),
    ("other capital", "Other Capital Contributions"),
    ("capital contributions", "Other Capital Contributions"),
    ("working capital", "Working Capital"),
    ("future taxes", "Future Taxes"),
    ("future tax", "Future Taxes"),
    ("capex/leasing", "Capex/Leasing"),
    ("capex", "Capex/Leasing"),
    ("leasing", "Capex/Leasing"),
    ("acquisitions", "Acquisitions"),
    ("acquisition", "Acquisitions"),
    ("dispositions", "Dispositions"),
    ("disposition", "Dispositions"),
    ("development", "Development"),
    ("asset mtm", "Asset MTM"),
    ("debt mtm", "Debt MTM"),
    ("mortgages", "Mortgages"),
    ("mortgage", "Mortgages"),
    ("hedges", "Hedges"),
    ("hedge", "Hedges"),
    ("miscellaneous", "Miscellaneous"),
    ("opening balance", "Opening"),
    ("opening", "Opening"),
)
BS_ALIASES = (
    ("3rd party", "3rd Party"),
    ("third party", "3rd Party"),
    ("real estate", "Real Estate"),
    ("gross asset value", "Real Estate"),
    ("debt", "Debt"),
    ("equity balance", "Equity"),
    ("equity value", "Equity"),
)
STRONG = (
    "portfolio",
    "asset",
    "noi",
    "net income",
    "aum",
    "ytd",
    "income statement",
    "equity",
    "capex",
    "waterfall",
    "variance",
    "return",
    "budget",
    "forecast",
    "actual",
    "bridge",
    "sector",
    "region",
    "country",
    "mtm",
    "g&a",
    "interest",
    "hierarchy",
    "kpis",
    "kpi",
)


@dataclass
class Plan:
    kind: str
    sql: str = ""
    params: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    normalized: str = ""


def normalize(question: str) -> str:
    text = question.strip().lower().replace("’", "'")
    text = text.replace("'s", " ")
    swaps = (
        ("what's", "what is"),
        ("whats", "what is"),
        ("how's", "how is"),
        ("hows", "how is"),
        ("year-to-date", "ytd"),
        ("year to date", "ytd"),
        ("y.t.d.", "ytd"),
        ("full-year", "annual"),
        ("full year", "annual"),
        ("operating plan", "budget"),
        ("mark-to-market", "mtm"),
        ("mark to market", "mtm"),
        ("third-party", "3rd party"),
        ("third party", "3rd party"),
        ("bottom line", "net income"),
        ("p&l", "income statement"),
        ("p and l", "income statement"),
        ("profit and loss", "income statement"),
        ("cap ex", "capex"),
        ("capital expenditure", "capex"),
        ("performance return", "return"),
        ("assets under management", "aum"),
        ("compared with", "vs"),
        ("compared to", "vs"),
        ("versus", "vs"),
        ("relative to", "vs"),
        ("asia pacific", "asia pac"),
        ("asia-pacific", "asia pac"),
        ("apac", "asia pac"),
        ("united kingdom", "uk"),
        ("u.s.a.", "usa"),
        ("u.s.", "usa"),
        ("canadian", "canada"),
        ("australian", "australia"),
        ("singaporean", "singapore"),
        ("european", "europe"),
        ("american", "usa"),
        ("british", "uk"),
    )
    for source, target in swaps:
        text = text.replace(source, target)
    text = re.sub(r"\b(property|building|holding)\s+([a-f])\b", r"asset \2", text)
    text = re.sub(r"[^a-z0-9&/%+.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _has(text: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in text
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000_000:
        return f"{sign}${amount / 1_000_000_000:.2f}bn"
    if amount >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.2f} million"
    return f"{sign}${amount:,.0f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.2f}%"


def _raw_sql(question: str) -> str | None:
    text = question.strip().rstrip(";").strip()
    if re.match(r"(?is)^(select|with)\b", text) and re.search(r"(?is)\bfrom\b", text):
        return text
    return None


def _scope(slots: dict) -> tuple[str, dict]:
    clauses = ["1 = 1"]
    params: dict = {}
    for key in ("asset_id", "region", "country", "sector"):
        if slots.get(key):
            clauses.append(f"{key} = :{key}")
            params[key] = slots[key]
    sql = (
        "scoped AS ("
        "SELECT asset_id, region, country, sector FROM hierarchy WHERE "
        + " AND ".join(clauses)
        + ")"
    )
    return sql, params


def _view(text: str, variance: bool) -> tuple[str, str]:
    ytd = "ytd" in text
    budget = _has(text, "budget")
    forecast = _has(text, "forecast") or (_has(text, "annual") and not variance)
    actual = _has(text, "actual")
    if variance:
        if ytd or (actual and not forecast):
            return "YTD", "Actual"
        return "Annual", "Forecast"
    if ytd and budget and not actual and not _has(text, "forecast"):
        return "YTD", "Budget"
    if ytd:
        return "YTD", "Actual"
    if budget and not forecast and not actual:
        return "Annual", "Budget"
    if actual and not forecast:
        return "YTD", "Actual"
    return "Annual", "Forecast"


def _bs_scenario(time_view: str, scenario: str) -> str:
    return {
        ("YTD", "Actual"): "YTD Actual",
        ("YTD", "Budget"): "YTD Actual",
        ("Annual", "Budget"): "Annual Budget",
    }.get((time_view, scenario), "Annual Forecast")


def _superlative(text: str) -> str | None:
    if _has(text, "rank") and not any(_has(text, word) for word in ("highest", "lowest", "best", "worst", "top", "bottom")):
        return "all"
    if any(_has(text, word) for word in ("lowest", "worst", "bottom", "smallest", "least")):
        return "low"
    if any(_has(text, word) for word in ("highest", "best", "top", "largest", "biggest", "most")):
        return "high"
    if _has(text, "rank"):
        return "all"
    return None


def _group(text: str) -> str | None:
    for phrase, column in (
        ("by asset", "asset_id"),
        ("per asset", "asset_id"),
        ("each asset", "asset_id"),
        ("by region", "region"),
        ("per region", "region"),
        ("each region", "region"),
        ("by country", "country"),
        ("per country", "country"),
        ("each country", "country"),
        ("by sector", "sector"),
        ("per sector", "sector"),
        ("each sector", "sector"),
    ):
        if phrase in text:
            return column
    return None


def _metrics(text: str) -> list[str]:
    found: list[str] = []
    for alias, metric in METRIC_ALIASES:
        if _has(text, alias) and metric not in found:
            found.append(metric)
    return found


def _equity_category(text: str) -> str | None:
    for alias, category in EQUITY_ALIASES:
        if _has(text, alias):
            return category
    return None


def _bs_category(text: str) -> str | None:
    for alias, category in BS_ALIASES:
        if _has(text, alias):
            return category
    if _has(text, "equity") and not _equity_category(text):
        return "Equity"
    return None


def _equity_scenario(text: str, scenarios: list[str]) -> str | None:
    for scenario in sorted(scenarios, key=len, reverse=True):
        if scenario.lower() in text:
            return scenario
    month_alias = (("december", "dec"), ("january", "jan"), ("june", "jun"))
    for scenario in scenarios:
        low = scenario.lower()
        for month, short in month_alias:
            if month in low and (_has(text, month) or _has(text, short)):
                return scenario
    return None


def _label(slots: dict) -> str:
    return slots.get("asset_id") or slots.get("country") or slots.get("sector") or slots.get("region") or "Portfolio"


def _portfolio_signal(text: str, slots: dict) -> bool:
    if any(slots.get(key) for key in ("asset_id", "region", "country", "sector", "unknown_asset")):
        return True
    if slots.get("metrics") or slots.get("equity_category") or slots.get("equity_scenario"):
        return True
    return any(_has(text, word) for word in STRONG)


def _extract(text: str, tables: dict[str, pd.DataFrame]) -> dict:
    slots: dict = {"metrics": _metrics(text)}
    assets = sorted(tables["hierarchy"]["asset_id"].unique(), key=len, reverse=True)
    for asset in assets:
        if _has(text, asset.lower()):
            slots["asset_id"] = asset
            break
    if "asset_id" not in slots:
        token = re.search(r"\basset\s+([a-z])\b", text)
        if token:
            name = f"Asset {token.group(1).upper()}"
            if name in set(assets):
                slots["asset_id"] = name
            else:
                slots["unknown_asset"] = name
    for column in ("region", "country", "sector"):
        labels = sorted(tables["hierarchy"][column].unique(), key=len, reverse=True)
        for label in labels:
            if _has(text, str(label).lower()):
                slots[column] = label
                break
    scenarios = tables["equity_bridge"]["scenario"].dropna().unique().tolist()
    equity_scenario = _equity_scenario(text, [str(item) for item in scenarios])
    if equity_scenario:
        slots["equity_scenario"] = equity_scenario
    category = _equity_category(text)
    if category:
        slots["equity_category"] = category
    if "mtm debt" not in text and "debt mtm" not in text:
        balance = _bs_category(text)
        if balance and "Net" not in " ".join(slots["metrics"]):
            slots["bs_category"] = balance
    if slots["metrics"] and slots.get("bs_category") == "Debt" and "Interest" in slots["metrics"]:
        slots.pop("bs_category", None)
    slots["variance"] = any(
        _has(text, word) for word in ("vs", "variance", "gap", "difference", "ahead", "behind", "shortfall")
    )
    slots["time_view"], slots["scenario"] = _view(text, slots["variance"])
    slots["superlative"] = _superlative(text)
    slots["group"] = _group(text)
    return slots


def _return_sql(scope_sql: str) -> str:
    return (
        f"WITH {scope_sql}, "
        "ni AS ("
        "SELECT asset_id, "
        "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Forecast' THEN amount END) AS ni_f, "
        "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Budget' THEN amount END) AS ni_b "
        "FROM kpis WHERE metric = 'Net Income' AND asset_id IN (SELECT asset_id FROM scoped) "
        "GROUP BY asset_id), "
        "eq AS ("
        "SELECT asset_id, "
        "SUM(CASE WHEN scenario = 'Annual Forecast' THEN amount END) AS eq_f, "
        "SUM(CASE WHEN scenario = 'Annual Budget' THEN amount END) AS eq_b "
        "FROM bs_by_region WHERE category = 'Equity' AND asset_id IN (SELECT asset_id FROM scoped) "
        "GROUP BY asset_id) "
        "SELECT s.asset_id, s.region, s.country, s.sector, ni.ni_f, ni.ni_b, eq.eq_f, eq.eq_b "
        "FROM scoped s LEFT JOIN ni ON ni.asset_id = s.asset_id "
        "LEFT JOIN eq ON eq.asset_id = s.asset_id ORDER BY s.asset_id"
    )


def _finish(sql: str, params: dict, meta: dict, text: str) -> Plan:
    used = {key: value for key, value in params.items() if f":{key}" in sql}
    return Plan("cte", sql, used, meta, text)


def build_plan(question: str, tables: dict[str, pd.DataFrame]) -> Plan | None:
    raw = _raw_sql(question)
    if raw:
        return Plan(kind="cte", sql=raw, meta={"shape": "raw"}, normalized=normalize(question))
    text = normalize(question)
    if not text:
        return None
    slots = _extract(text, tables)
    if slots.get("unknown_asset"):
        return Plan(kind="refuse", normalized=text)
    if not _portfolio_signal(text, slots):
        return None

    scope_sql, params = _scope(slots)
    meta = {
        "label": _label(slots),
        "time_view": slots["time_view"],
        "scenario": slots["scenario"],
        "variance": slots["variance"],
        "superlative": slots["superlative"],
        "group": slots["group"],
        "metrics": slots["metrics"],
        "equity_category": slots.get("equity_category"),
        "bs_category": slots.get("bs_category"),
    }
    equity_context = bool(slots.get("equity_scenario") or slots.get("equity_category") or _has(text, "bridge") or _has(text, "waterfall"))
    want_return = _has(text, "return") or _has(text, "yield") or _has(text, "performing")
    want_list = any(
        phrase in text
        for phrase in (
            "list asset",
            "list the asset",
            "show asset",
            "show the asset",
            "which asset",
            "what asset",
            "what are the asset",
            "all asset",
        )
    )
    want_count = "how many" in text and "asset" in text
    want_statement = "income statement" in text or "all line" in text or "all metric" in text or "every metric" in text
    want_is_total = not slots["metrics"] and (
        ("income statement" in text and "total" in text)
        or (
            "variance" in text
            and "percent" in text
            and not any(slots.get(key) for key in ("asset_id", "region", "country", "sector"))
        )
    )
    want_watch = ("both" in text and any(word in text for word in ("behind", "short", "negative", "miss"))) or "watchlist" in text
    want_miss = slots["superlative"] in {"high", "low"} and any(word in text for word in ("gap", "variance", "miss", "shortfall")) and not slots["metrics"]
    want_aum = _has(text, "aum")

    if want_is_total:
        sql = (
            f"WITH {scope_sql}, totals AS ("
            "SELECT "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Actual' THEN amount END) AS ytd_actual, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Budget' THEN amount END) AS ytd_budget, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Forecast' THEN amount END) AS annual_forecast, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Budget' THEN amount END) AS annual_budget "
            "FROM kpis WHERE asset_id IN (SELECT asset_id FROM scoped)) "
            "SELECT ytd_actual, ytd_budget, annual_forecast, annual_budget FROM totals"
        )
        return _finish(sql, params, {**meta, "shape": "statement_total"}, text)
    if want_count:
        return _finish( f"WITH {scope_sql} SELECT COUNT(*) AS n FROM scoped", params, {**meta, "shape": "count"}, text)
    if want_watch:
        sql = (
            f"WITH {scope_sql}, lines AS ("
            "SELECT h.asset_id, h.country, h.sector, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Actual' THEN amount END) AS ytd_actual, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Budget' THEN amount END) AS ytd_budget, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Forecast' THEN amount END) AS annual_forecast, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Budget' THEN amount END) AS annual_budget "
            "FROM kpis k JOIN scoped h ON h.asset_id = k.asset_id "
            "WHERE k.metric = 'Net Income' GROUP BY h.asset_id, h.country, h.sector) "
            "SELECT asset_id, country, sector FROM lines "
            "WHERE ytd_actual < ytd_budget AND annual_forecast < annual_budget "
            "ORDER BY (annual_forecast - annual_budget)"
        )
        return _finish( sql, params, {**meta, "shape": "watch"}, text)
    if want_miss:
        sql = (
            f"WITH {scope_sql}, lines AS ("
            "SELECT metric, "
            "SUM(CASE WHEN scenario = 'Forecast' THEN amount END) AS forecast, "
            "SUM(CASE WHEN scenario = 'Budget' THEN amount END) AS budget "
            "FROM kpis WHERE time_view = 'Annual' AND asset_id IN (SELECT asset_id FROM scoped) "
            "GROUP BY metric) "
            "SELECT metric, forecast, budget FROM lines ORDER BY (forecast - budget) ASC LIMIT 1"
        )
        return _finish( sql, params, {**meta, "shape": "miss"}, text)
    if want_return or (slots["superlative"] and not slots["metrics"] and not equity_context):
        return _finish( _return_sql(scope_sql), params, {**meta, "shape": "return"}, text)
    if want_aum:
        sql = (
            f"WITH {scope_sql}, balances AS ("
            "SELECT scenario, SUM(amount) AS amount FROM bs_by_region "
            "WHERE category IN ('Equity', 'Debt', '3rd Party') "
            "AND asset_id IN (SELECT asset_id FROM scoped) GROUP BY scenario) "
            "SELECT scenario, amount FROM balances"
        )
        return _finish( sql, params, {**meta, "shape": "aum"}, text)
    if equity_context and not slots["metrics"]:
        scenario = slots.get("equity_scenario")
        if not scenario:
            names = [str(item) for item in tables["equity_bridge"]["scenario"].dropna().unique()]
            scenario = "December 2019" if "December 2019" in names else (names[0] if names else "")
        if not scenario:
            return Plan("refuse", normalized=text)
        params = {**params, "equity_scenario": scenario}
        where = "scenario = :equity_scenario"
        if slots.get("equity_category"):
            where += " AND attribution_category = :equity_category"
            params["equity_category"] = slots["equity_category"]
        if slots.get("region"):
            where += " AND region = :region"
        sql = (
            "WITH bridge AS ("
            "SELECT attribution_category, MIN(sort_order) AS sort_order, SUM(bridge) AS amount "
            f"FROM equity_bridge WHERE {where} GROUP BY attribution_category) "
            "SELECT attribution_category, amount FROM bridge ORDER BY sort_order"
        )
        meta = {**meta, "shape": "equity", "equity_scenario": scenario, "region": slots.get("region")}
        return _finish( sql, params, meta, text)
    if want_statement or (len(slots["metrics"]) > 1 and not slots["variance"]):
        metrics = slots["metrics"]
        metric_filter = ""
        if metrics and not want_statement:
            names = []
            for index, metric in enumerate(metrics):
                key = f"m{index}"
                params[key] = metric
                names.append(f":{key}")
            metric_filter = " AND metric IN (" + ", ".join(names) + ")"
        sql = (
            f"WITH {scope_sql}, lines AS ("
            "SELECT metric, MIN(metric_sort) AS metric_sort, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Actual' THEN amount END) AS ytd_actual, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Budget' THEN amount END) AS ytd_budget, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Forecast' THEN amount END) AS annual_forecast, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Budget' THEN amount END) AS annual_budget "
            "FROM kpis WHERE asset_id IN (SELECT asset_id FROM scoped)"
            f"{metric_filter} GROUP BY metric) "
            "SELECT metric, ytd_actual, ytd_budget, annual_forecast, annual_budget FROM lines ORDER BY metric_sort"
        )
        return _finish( sql, params, {**meta, "shape": "statement"}, text)
    if slots.get("bs_category") and not slots["metrics"]:
        params = {**params, "bs_category": slots["bs_category"], "bs_scenario": _bs_scenario(slots["time_view"], slots["scenario"])}
        group = slots["group"] or "asset_id"
        if group not in {"asset_id", "region", "country", "sector"}:
            group = "asset_id"
        sql = (
            f"WITH {scope_sql}, balances AS ("
            f"SELECT s.{group} AS bucket, SUM(b.amount) AS amount "
            "FROM bs_by_region b JOIN scoped s ON s.asset_id = b.asset_id "
            "WHERE b.category = :bs_category AND b.scenario = :bs_scenario "
            f"GROUP BY s.{group}) "
            "SELECT bucket, amount FROM balances ORDER BY amount DESC"
        )
        if not slots["group"]:
            sql = (
                f"WITH {scope_sql}, balances AS ("
                "SELECT SUM(amount) AS amount FROM bs_by_region "
                "WHERE category = :bs_category AND scenario = :bs_scenario "
                "AND asset_id IN (SELECT asset_id FROM scoped)) "
                "SELECT amount FROM balances"
            )
        return _finish( sql, params, {**meta, "shape": "balance", "group": slots["group"]}, text)
    if slots["metrics"]:
        params = {**params, "metric": slots["metrics"][0], "time_view": slots["time_view"], "scenario": slots["scenario"]}
        if slots["group"]:
            column = slots["group"]
            sql = (
                f"WITH {scope_sql}, lines AS ("
                f"SELECT s.{column} AS bucket, SUM(k.amount) AS amount "
                "FROM kpis k JOIN scoped s ON s.asset_id = k.asset_id "
                "WHERE k.metric = :metric AND k.time_view = :time_view AND k.scenario = :scenario "
                f"GROUP BY s.{column}) "
                "SELECT bucket, amount FROM lines ORDER BY amount DESC"
            )
            return _finish( sql, params, {**meta, "shape": "group"}, text)
        if slots["variance"]:
            sql = (
                f"WITH {scope_sql}, lines AS ("
                "SELECT scenario, SUM(amount) AS amount FROM kpis "
                "WHERE metric = :metric AND time_view = :time_view "
                "AND asset_id IN (SELECT asset_id FROM scoped) GROUP BY scenario) "
                "SELECT "
                "(SELECT amount FROM lines WHERE scenario = :scenario) AS left_amount, "
                "(SELECT amount FROM lines WHERE scenario = 'Budget') AS budget"
            )
            return _finish( sql, params, {**meta, "shape": "variance"}, text)
        if slots["superlative"]:
            sql = (
                f"WITH {scope_sql}, lines AS ("
                "SELECT s.asset_id AS bucket, SUM(k.amount) AS amount "
                "FROM kpis k JOIN scoped s ON s.asset_id = k.asset_id "
                "WHERE k.metric = :metric AND k.time_view = :time_view AND k.scenario = :scenario "
                "GROUP BY s.asset_id) "
                "SELECT bucket, amount FROM lines ORDER BY amount DESC"
            )
            return _finish( sql, params, {**meta, "shape": "group"}, text)
        sql = (
            f"WITH {scope_sql}, lines AS ("
            "SELECT SUM(amount) AS amount FROM kpis "
            "WHERE metric = :metric AND time_view = :time_view AND scenario = :scenario "
            "AND asset_id IN (SELECT asset_id FROM scoped)) "
            "SELECT amount FROM lines"
        )
        return _finish( sql, params, {**meta, "shape": "amount"}, text)
    if want_list or (slots.get("asset_id") and not slots["metrics"]):
        if slots.get("asset_id") and not want_list:
            return _finish( _return_sql(scope_sql), params, {**meta, "shape": "snapshot"}, text)
        sql = f"WITH {scope_sql} SELECT asset_id, region, country, sector FROM scoped ORDER BY asset_id"
        return _finish( sql, params, {**meta, "shape": "list"}, text)
    if _has(text, "portfolio") or _has(text, "hierarchy") or _has(text, "kpi"):
        sql = f"WITH {scope_sql} SELECT asset_id, region, country, sector FROM scoped ORDER BY asset_id"
        return _finish( sql, params, {**meta, "shape": "list"}, text)
    return None


def _rates(frame: pd.DataFrame) -> list[tuple[str, float, str, str, str]]:
    rows = []
    for row in frame.itertuples(index=False):
        equity = float(row.eq_f or 0)
        if not equity:
            continue
        rows.append((row.asset_id, float(row.ni_f or 0) / equity, row.region, row.country, row.sector))
    rows.sort(key=lambda item: item[1], reverse=True)
    return rows


def _blended(frame: pd.DataFrame, label: str) -> str:
    ni_f = float(frame["ni_f"].sum(skipna=True) or 0)
    ni_b = float(frame["ni_b"].sum(skipna=True) or 0)
    eq_f = float(frame["eq_f"].sum(skipna=True) or 0)
    eq_b = float(frame["eq_b"].sum(skipna=True) or 0)
    if not eq_f or not eq_b:
        return REFUSAL
    forecast = ni_f / eq_f
    budget = ni_b / eq_b
    return (
        f"{label} forecast return is {forecast * 100:.2f}% on net income {_money(ni_f)}. "
        f"Budget return is {budget * 100:.2f}% on net income {_money(ni_b)}. "
        f"The variance is {(forecast - budget) * 100:+.2f} points."
    )


def _statement_total_sentence(label: str, row: pd.Series) -> str:
    actual = float(row["ytd_actual"] or 0)
    budget = float(row["ytd_budget"] or 0)
    forecast = float(row["annual_forecast"] or 0)
    annual = float(row["annual_budget"] or 0)
    heading = "Total" if label == "Total" else f"{label} income statement total"
    return (
        f"{heading}: YTD actual {_money(actual)} vs YTD budget {_money(budget)} "
        f"(YTD Var % {_pct(variance_pct(actual, budget))}), and annual forecast {_money(forecast)} "
        f"vs annual budget {_money(annual)} (Annual Var % {_pct(variance_pct(forecast, annual))})"
    )


def speak_result(meta: dict, frame: pd.DataFrame) -> str:
    shape = meta.get("shape")
    if frame.empty:
        return REFUSAL
    if shape == "raw":
        preview = frame.head(8)
        lines = [", ".join(f"{col}={row[col]}" for col in preview.columns) for _, row in preview.iterrows()]
        extra = "" if len(frame) <= 8 else f" Showing 8 of {len(frame)}."
        return f"{len(frame)} rows.{extra} " + " | ".join(lines)
    if shape == "count":
        return f"There are {int(frame['n'].iloc[0])} assets in this selection."
    if shape == "list":
        names = [f"{row.asset_id} ({row.country}, {row.sector}, {row.region})" for row in frame.itertuples(index=False)]
        return "Assets: " + "; ".join(names) + "."
    if shape == "watch":
        names = [f"{row.asset_id} ({row.country}, {row.sector})" for row in frame.itertuples(index=False)]
        if not names:
            return "No asset is behind budget on both YTD and the annual forecast."
        return "These assets are behind on both YTD and the annual forecast: " + ", ".join(names) + "."
    if shape == "miss":
        row = frame.iloc[0]
        gap = float(row["forecast"] or 0) - float(row["budget"] or 0)
        return (
            f"The largest annual dollar gap is {row['metric']}: forecast {_money(float(row['forecast'] or 0))} "
            f"vs budget {_money(float(row['budget'] or 0))}, a variance of {_money(gap)} "
            f"({_pct(variance_pct(float(row['forecast'] or 0), float(row['budget'] or 0)))})."
        )
    if shape in {"return", "snapshot"}:
        label = meta.get("label") or "Portfolio"
        if meta.get("superlative") == "all" or meta.get("group") == "asset_id":
            parts = [f"{asset} {rate * 100:.2f}%" for asset, rate, *_rest in _rates(frame)]
            if not parts:
                return REFUSAL
            return "Forecast return by asset: " + ", ".join(parts) + "."
        if meta.get("group") in {"region", "country", "sector"}:
            column = meta["group"]
            parts = []
            for bucket, part in frame.groupby(column):
                sentence = _blended(part, str(bucket))
                if sentence != REFUSAL:
                    parts.append(sentence)
            return " ".join(parts) if parts else REFUSAL
        if meta.get("superlative") in {"high", "low"}:
            ranked = _rates(frame)
            if not ranked:
                return REFUSAL
            asset, rate, *_rest = ranked[-1] if meta["superlative"] == "low" else ranked[0]
            word = "lowest" if meta["superlative"] == "low" else "highest"
            return f"The {word} forecast return is {asset} at {rate * 100:.2f}%."
        if shape == "snapshot":
            row = frame.iloc[0]
            detail = f"{row.asset_id} is {row.sector} in {row.country}, {row.region}. "
            return detail + _blended(frame, row.asset_id)
        return _blended(frame, label)
    if shape == "aum":
        parts = [f"{row.scenario} {_money(float(row.amount or 0))}" for row in frame.itertuples(index=False)]
        return "Assets under management, equity plus debt plus third party: " + "; ".join(parts) + "."
    if shape == "equity":
        scenario = meta.get("equity_scenario")
        where = meta.get("region") or "all regions"
        if meta.get("equity_category"):
            amount = float(frame["amount"].sum())
            return f"{scenario} {meta['equity_category']} for {where} is {_money(amount)}."
        opening = frame.loc[frame["attribution_category"] == "Opening", "amount"]
        total = float(frame["amount"].sum())
        if opening.empty:
            return REFUSAL
        return f"{scenario} opening equity for {where} is {_money(float(opening.iloc[0]))} and the total is {_money(total)}."
    if shape == "statement_total":
        return _statement_total_sentence(meta.get("label") or "Portfolio", frame.iloc[0]) + "."
    if shape == "statement":
        lines = []
        ytd_actual = ytd_budget = annual_forecast = annual_budget = 0.0
        for row in frame.itertuples(index=False):
            actual = float(row.ytd_actual or 0)
            budget = float(row.ytd_budget or 0)
            forecast = float(row.annual_forecast or 0)
            annual = float(row.annual_budget or 0)
            ytd_actual += actual
            ytd_budget += budget
            annual_forecast += forecast
            annual_budget += annual
            lines.append(
                f"{row.metric}: YTD actual {_money(actual)} vs budget {_money(budget)} "
                f"({_pct(variance_pct(actual, budget))}), annual forecast {_money(forecast)} "
                f"vs budget {_money(annual)} ({_pct(variance_pct(forecast, annual))})"
            )
        total_row = pd.Series(
            {
                "ytd_actual": ytd_actual,
                "ytd_budget": ytd_budget,
                "annual_forecast": annual_forecast,
                "annual_budget": annual_budget,
            }
        )
        lines.append(_statement_total_sentence("Total", total_row))
        return f"{meta.get('label')} income statement. " + "; ".join(lines) + "."
    if shape == "balance":
        if "bucket" in frame.columns:
            parts = [f"{row.bucket} {_money(float(row.amount or 0))}" for row in frame.itertuples(index=False)]
            return f"{meta.get('bs_category')} for {meta.get('time_view')} {meta.get('scenario')}: " + "; ".join(parts) + "."
        return (
            f"{meta.get('label')} {meta.get('bs_category')} is {_money(float(frame['amount'].iloc[0] or 0))}."
        )
    if shape == "group":
        metric = (meta.get("metrics") or ["value"])[0]
        parts = [f"{row.bucket} {_money(float(row.amount or 0))}" for row in frame.itertuples(index=False)]
        word = "highest" if meta.get("superlative") == "high" else "lowest" if meta.get("superlative") == "low" else "by group"
        if meta.get("superlative") in {"high", "low"} and parts:
            pick = parts[-1] if meta["superlative"] == "low" else parts[0]
            return f"The {word} {metric} is {pick}."
        return f"{metric} for {meta.get('time_view')} {meta.get('scenario')}: " + "; ".join(parts) + "."
    if shape == "variance":
        left = float(frame["left_amount"].iloc[0] or 0)
        budget = float(frame["budget"].iloc[0] or 0)
        metric = (meta.get("metrics") or ["value"])[0]
        gap = left - budget
        return (
            f"{meta.get('label')} {metric} is {_money(left)} vs budget {_money(budget)}. "
            f"The variance is {_money(gap)} ({_pct(variance_pct(left, budget))})."
        )
    if shape == "amount":
        metric = (meta.get("metrics") or ["value"])[0]
        amount = frame["amount"].iloc[0]
        if amount is None or (isinstance(amount, float) and pd.isna(amount)):
            return REFUSAL
        return (
            f"{meta.get('label')} {metric} for {meta.get('time_view')} {meta.get('scenario')} "
            f"is {_money(float(amount))}."
        )
    return REFUSAL
