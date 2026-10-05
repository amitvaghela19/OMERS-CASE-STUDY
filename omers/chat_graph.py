"""LangGraph router. Answers come from SQL templates or a saved question, never from a model."""

from __future__ import annotations

import json
import re
from contextvars import ContextVar
from difflib import SequenceMatcher
from pathlib import Path
from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from omers.metrics import variance_pct
from omers.nl_sql import build_plan, speak_result
from omers.store import load_tables, run_select

REFUSAL = "I don't know the answer, but I will get back to you."
CORPUS = Path(__file__).resolve().parents[1] / "chatbot" / "corpus"
RELEVANT_FILES = (
    "relevant_amounts.json",
    "relevant_variances.json",
    "relevant_equity.json",
    "relevant_portfolio.json",
    "relevant_extra.json",
)
_TABLES: ContextVar[dict | None] = ContextVar("omers_chat_tables", default=None)
_TEXT_INDEX: dict[str, list[tuple[str, dict]]] = {}

METRIC_ALIASES = (
    ("recoverable capital", "Recoverable Capital Amort"),
    ("other gain / loss", "Other Gain / Loss"),
    ("other gains", "Other Gain / Loss"),
    ("other gain", "Other Gain / Loss"),
    ("current income tax", "Current Income Tax"),
    ("income tax", "Current Income Tax"),
    ("current capital tax", "Current Capital Tax"),
    ("capital tax", "Current Capital Tax"),
    ("mtm real estate", "MTM Assets"),
    ("mtm assets", "MTM Assets"),
    ("mtm debt", "MTM Debt"),
    ("mark-to-market debt", "MTM Debt"),
    ("mark-to-market assets", "MTM Assets"),
    ("net income", "Net Income"),
    ("net g&a", "Net G&A"),
    ("ff&e", "FF&E Amort"),
    ("interest", "Interest"),
    ("noi", "NOI"),
)
BS_ALIASES = (
    ("3rd party", "3rd Party"),
    ("third party", "3rd Party"),
    ("real estate", "Real Estate"),
    ("debt", "Debt"),
)
VIEW_PHRASES = (
    ("ytd actual", "YTD", "Actual"),
    ("year to date actual", "YTD", "Actual"),
    ("ytd budget", "YTD", "Budget"),
    ("annual forecast", "Annual", "Forecast"),
    ("full year forecast", "Annual", "Forecast"),
    ("annual budget", "Annual", "Budget"),
    ("forecast", "Annual", "Forecast"),
    ("budget", "Annual", "Budget"),
)


class ChatState(TypedDict, total=False):
    question: str
    normalized: str
    route: str
    sql_id: str
    params: dict
    sql_text: str
    answer: str
    meta: dict


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


def _load_json(name: str) -> list[dict]:
    path = CORPUS / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _texts(name: str) -> list[tuple[str, dict]]:
    if name not in _TEXT_INDEX:
        rows: list[tuple[str, dict]] = []
        for row in _load_json(name):
            for text in [row.get("question", ""), *row.get("paraphrases", []), *row.get("examples", [])]:
                if text:
                    rows.append((_normalize(text), row))
        _TEXT_INDEX[name] = rows
    return _TEXT_INDEX[name]


def _exact(normalized: str, names: tuple[str, ...]) -> dict | None:
    for name in names:
        for text, row in _texts(name):
            if text == normalized:
                return row
    return None


def _fuzzy(normalized: str, names: tuple[str, ...]) -> tuple[float, dict | None]:
    words = set(normalized.split())
    best = 0.0
    found = None
    for name in names:
        for text, row in _texts(name):
            tokens = set(text.split())
            if not words or not tokens:
                continue
            overlap = len(words & tokens) / max(len(words), len(tokens))
            if overlap < 0.55:
                continue
            score = overlap if overlap >= 0.98 else _similarity(normalized, text)
            if score > best:
                best = score
                found = row
    return best, found


def _contains(normalized: str, label: str) -> bool:
    return label.lower() in normalized


def _extract(normalized: str, tables: dict[str, pd.DataFrame]) -> dict:
    found: dict = {}
    assets = sorted(tables["hierarchy"]["asset_id"].unique(), key=len, reverse=True)
    for asset in assets:
        if _contains(normalized, asset):
            found["asset_id"] = asset
            break
    if "asset_id" not in found:
        token = re.search(r"\basset\s+([a-z])\b", normalized)
        if token:
            found["unknown_asset"] = f"Asset {token.group(1).upper()}"
    for column in ("region", "country", "sector"):
        labels = sorted(tables["hierarchy"][column].unique(), key=len, reverse=True)
        for label in labels:
            if _contains(normalized, label):
                found[column] = label
                break
    for alias, metric in METRIC_ALIASES:
        if alias in normalized:
            found["metric"] = metric
            break
    if "metric" not in found and "equity_scenario" not in found:
        for alias, category in BS_ALIASES:
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                found["bs_category"] = category
                break
        if "bs_category" not in found and re.search(r"\bequity\b", normalized):
            found["bs_category"] = "Equity"
    for phrase, time_view, scenario in VIEW_PHRASES:
        if phrase in normalized:
            found["time_view"] = time_view
            found["scenario"] = scenario
            found["view_label"] = phrase
            break
    categories = sorted(tables["equity_bridge"]["attribution_category"].unique(), key=len, reverse=True)
    for category in categories:
        if category.lower() in normalized:
            found["category"] = category
            break
    for scenario in sorted(tables["equity_bridge"]["scenario"].unique(), key=len, reverse=True):
        if scenario.lower() in normalized:
            found["equity_scenario"] = scenario
            break
    return found


def _intent(normalized: str, slots: dict) -> tuple[str, dict] | None:
    if slots.get("unknown_asset"):
        return None
    if any(word in normalized for word in ("largest", "biggest", "worst")) and any(
        word in normalized for word in ("gap", "variance", "miss", "shortfall")
    ):
        return "largest_miss", {}
    if "return" in normalized and any(word in normalized for word in ("highest", "lowest", "best", "worst", "rank")):
        if "rank" in normalized and not any(word in normalized for word in ("highest", "lowest", "best", "worst")):
            direction = "all"
        elif any(word in normalized for word in ("lowest", "worst")):
            direction = "low"
        else:
            direction = "high"
        return "asset_rank", {"direction": direction}
    if "which asset" in normalized or ("behind" in normalized and "both" in normalized):
        return "watchlist", {}
    if "assets under management" in normalized or normalized.strip() == "aum" or " aum" in f" {normalized}":
        return "aum", {}
    if "return" in normalized and slots.get("asset_id"):
        return "asset_return", {"asset_id": slots["asset_id"]}
    if "return" in normalized and any(slots.get(key) for key in ("region", "country", "sector")):
        params = {key: slots[key] for key in ("region", "country", "sector") if slots.get(key)}
        return "geo_return", params
    if "return" in normalized and not slots.get("asset_id"):
        return "portfolio_return", {}
    if slots.get("category") and slots.get("equity_scenario"):
        params = {"scenario": slots["equity_scenario"], "category": slots["category"]}
        if slots.get("region"):
            params["region"] = slots["region"]
        return "equity_category", params
    if slots.get("equity_scenario") and any(word in normalized for word in ("opening", "total", "closing", "equity")):
        return "equity_total", {"scenario": slots["equity_scenario"]}
    if slots.get("bs_category") and slots.get("asset_id") and not slots.get("equity_scenario"):
        scenario = {
            ("YTD", "Actual"): "YTD Actual",
            ("Annual", "Budget"): "Annual Budget",
        }.get((slots.get("time_view"), slots.get("scenario")), "Annual Forecast")
        return "bs_amount", {
            "asset_id": slots["asset_id"],
            "category": slots["bs_category"],
            "scenario": scenario,
        }
    if slots.get("metric") and not slots.get("asset_id") and any(slots.get(key) for key in ("region", "country", "sector")):
        params = {
            "metric": slots["metric"],
            "time_view": slots.get("time_view") or "Annual",
            "scenario": slots.get("scenario") or "Forecast",
        }
        for key in ("region", "country", "sector"):
            if slots.get(key):
                params[key] = slots[key]
        return "geo_kpi", params
    if slots.get("asset_id") and slots.get("metric"):
        params = {
            "asset_id": slots["asset_id"],
            "metric": slots["metric"],
            "time_view": slots.get("time_view") or "Annual",
            "scenario": slots.get("scenario") or "Forecast",
        }
        if any(word in normalized for word in ("variance", "versus", "vs budget", "ahead", "behind")):
            return "kpi_variance", params
        return "kpi_amount", params
    return None


def prepare(state: ChatState) -> ChatState:
    tables = _TABLES.get()
    if not tables:
        return {"route": "refuse", "answer": REFUSAL}
    plan = build_plan(state["question"], tables)
    if plan is not None:
        if plan.kind == "refuse":
            return {"route": "refuse", "normalized": plan.normalized}
        return {
            "route": "sql",
            "sql_id": "cte",
            "params": plan.params,
            "sql_text": plan.sql,
            "meta": plan.meta,
            "normalized": plan.normalized,
        }
    normalized = _normalize(state["question"])
    slots = _extract(normalized, tables)
    intent = _intent(normalized, slots)
    has_entity = any(
        key in slots for key in ("asset_id", "region", "country", "sector", "metric", "category", "equity_scenario")
    )
    relevant = None
    if slots.get("unknown_asset"):
        route = "refuse"
    elif intent:
        route = "sql"
    else:
        relevant = _exact(normalized, RELEVANT_FILES) or _exact(normalized, ("nl_sql.json",))
        irrelevant = _exact(normalized, ("irrelevant.json",))
        if irrelevant and not has_entity:
            route = "refuse"
            relevant = None
        elif relevant and relevant.get("sql_id"):
            route = "saved"
        else:
            irr_score, _ = _fuzzy(normalized, ("irrelevant.json",))
            rel_score, relevant = _fuzzy(normalized, RELEVANT_FILES)
            if not relevant or rel_score < 0.84:
                nl_score, nl_row = _fuzzy(normalized, ("nl_sql.json",))
                if nl_row and nl_score >= rel_score and nl_score >= 0.84 and nl_row.get("sql_id"):
                    relevant = nl_row
                    rel_score = nl_score
            if relevant and relevant.get("sql_id") and rel_score >= 0.84 and rel_score >= irr_score:
                route = "saved"
            else:
                route = "refuse"
                relevant = None
    update: ChatState = {"normalized": normalized, "route": route}
    if route == "sql" and intent:
        update["sql_id"] = intent[0]
        update["params"] = intent[1]
    elif route == "saved" and relevant:
        update["sql_id"] = relevant["sql_id"]
        update["params"] = relevant.get("params", {})
    return update


def _run(sql: str, params: dict | None = None) -> pd.DataFrame:
    return run_select(sql, params=params or None, source="chat")


def _return_sentence(label: str, row: pd.Series) -> str:
    ni_f = float(row["ni_f"] or 0)
    ni_b = float(row["ni_b"] or 0)
    eq_f = float(row["eq_f"] or 0)
    eq_b = float(row["eq_b"] or 0)
    if not eq_f or not eq_b:
        return REFUSAL
    forecast = ni_f / eq_f
    budget = ni_b / eq_b
    return (
        f"{label} forecast return is {forecast * 100:.2f}% on net income {_money(ni_f)}. "
        f"Budget return is {budget * 100:.2f}% on net income {_money(ni_b)}. "
        f"The variance is {(forecast - budget) * 100:+.2f} points."
    )


def _speak(sql_id: str, params: dict) -> tuple[str, str]:
    if sql_id == "kpi_amount":
        sql = (
            "SELECT COALESCE(SUM(amount), 0) AS amount FROM kpis "
            "WHERE asset_id = :asset_id AND metric = :metric "
            "AND time_view = :time_view AND scenario = :scenario"
        )
        frame = _run(sql, params)
        amount = float(frame["amount"].iloc[0])
        return sql, (
            f"{params['asset_id']} {params['metric']} for {params['time_view']} {params['scenario']} "
            f"is {_money(amount)}."
        )
    if sql_id == "kpi_variance":
        sql = (
            "SELECT "
            "SUM(CASE WHEN scenario = :scenario THEN amount END) AS left_amount, "
            "SUM(CASE WHEN scenario = 'Budget' THEN amount END) AS budget "
            "FROM kpis WHERE asset_id = :asset_id AND metric = :metric AND time_view = :time_view"
        )
        frame = _run(sql, params)
        left = float(frame["left_amount"].iloc[0] or 0)
        budget = float(frame["budget"].iloc[0] or 0)
        gap = left - budget
        return sql, (
            f"{params['asset_id']} {params['metric']} is {_money(left)} vs budget {_money(budget)}. "
            f"The variance is {_money(gap)} ({_pct(variance_pct(left, budget))})."
        )
    if sql_id == "asset_return":
        sql = (
            "SELECT "
            "(SELECT SUM(amount) FROM kpis WHERE asset_id = :asset_id AND metric = 'Net Income' "
            "AND time_view = 'Annual' AND scenario = 'Forecast') AS ni_f, "
            "(SELECT SUM(amount) FROM kpis WHERE asset_id = :asset_id AND metric = 'Net Income' "
            "AND time_view = 'Annual' AND scenario = 'Budget') AS ni_b, "
            "(SELECT SUM(amount) FROM bs_by_region WHERE asset_id = :asset_id AND category = 'Equity' "
            "AND scenario = 'Annual Forecast') AS eq_f, "
            "(SELECT SUM(amount) FROM bs_by_region WHERE asset_id = :asset_id AND category = 'Equity' "
            "AND scenario = 'Annual Budget') AS eq_b"
        )
        frame = _run(sql, params)
        return sql, _return_sentence(params["asset_id"], frame.iloc[0])
    if sql_id == "portfolio_return":
        sql = (
            "SELECT "
            "(SELECT SUM(amount) FROM kpis WHERE metric = 'Net Income' AND time_view = 'Annual' AND scenario = 'Forecast') AS ni_f, "
            "(SELECT SUM(amount) FROM kpis WHERE metric = 'Net Income' AND time_view = 'Annual' AND scenario = 'Budget') AS ni_b, "
            "(SELECT SUM(amount) FROM bs_by_region WHERE category = 'Equity' AND scenario = 'Annual Forecast') AS eq_f, "
            "(SELECT SUM(amount) FROM bs_by_region WHERE category = 'Equity' AND scenario = 'Annual Budget') AS eq_b"
        )
        frame = _run(sql)
        return sql, _return_sentence("Portfolio", frame.iloc[0])
    if sql_id == "geo_return":
        clauses = []
        bind: dict = {}
        for key in ("region", "country", "sector"):
            if params.get(key):
                clauses.append(f"{key} = :{key}")
                bind[key] = params[key]
        where = " AND ".join(clauses)
        sql = (
            "SELECT "
            f"(SELECT SUM(amount) FROM kpis WHERE metric = 'Net Income' AND time_view = 'Annual' AND scenario = 'Forecast' "
            f"AND asset_id IN (SELECT asset_id FROM hierarchy WHERE {where})) AS ni_f, "
            f"(SELECT SUM(amount) FROM kpis WHERE metric = 'Net Income' AND time_view = 'Annual' AND scenario = 'Budget' "
            f"AND asset_id IN (SELECT asset_id FROM hierarchy WHERE {where})) AS ni_b, "
            f"(SELECT SUM(amount) FROM bs_by_region WHERE category = 'Equity' AND scenario = 'Annual Forecast' "
            f"AND asset_id IN (SELECT asset_id FROM hierarchy WHERE {where})) AS eq_f, "
            f"(SELECT SUM(amount) FROM bs_by_region WHERE category = 'Equity' AND scenario = 'Annual Budget' "
            f"AND asset_id IN (SELECT asset_id FROM hierarchy WHERE {where})) AS eq_b"
        )
        frame = _run(sql, bind)
        label = params.get("country") or params.get("sector") or params.get("region") or "Selection"
        return sql, _return_sentence(str(label), frame.iloc[0])
    if sql_id == "geo_kpi":
        clauses = []
        bind = {
            "metric": params["metric"],
            "time_view": params["time_view"],
            "scenario": params["scenario"],
        }
        for key in ("region", "country", "sector"):
            if params.get(key):
                clauses.append(f"{key} = :{key}")
                bind[key] = params[key]
        where = " AND ".join(clauses)
        sql = (
            "SELECT COALESCE(SUM(amount), 0) AS amount FROM kpis "
            "WHERE metric = :metric AND time_view = :time_view AND scenario = :scenario "
            f"AND asset_id IN (SELECT asset_id FROM hierarchy WHERE {where})"
        )
        frame = _run(sql, bind)
        place = params.get("country") or params.get("sector") or params.get("region")
        return sql, (
            f"{place} {params['metric']} for {params['time_view']} {params['scenario']} "
            f"is {_money(float(frame['amount'].iloc[0]))}."
        )
    if sql_id == "bs_amount":
        sql = (
            "SELECT COALESCE(SUM(amount), 0) AS amount FROM bs_by_region "
            "WHERE asset_id = :asset_id AND category = :category AND scenario = :scenario"
        )
        frame = _run(sql, params)
        return sql, (
            f"{params['asset_id']} {params['category']} for {params['scenario']} "
            f"is {_money(float(frame['amount'].iloc[0]))}."
        )
    if sql_id == "asset_rank":
        sql = (
            "SELECT h.asset_id, "
            "(SELECT SUM(amount) FROM kpis WHERE asset_id = h.asset_id AND metric = 'Net Income' "
            "AND time_view = 'Annual' AND scenario = 'Forecast') AS ni_f, "
            "(SELECT SUM(amount) FROM bs_by_region WHERE asset_id = h.asset_id AND category = 'Equity' "
            "AND scenario = 'Annual Forecast') AS eq_f "
            "FROM hierarchy h ORDER BY h.asset_id"
        )
        frame = _run(sql)
        ranked = []
        for row in frame.itertuples(index=False):
            equity = float(row.eq_f or 0)
            if not equity:
                continue
            ranked.append((row.asset_id, float(row.ni_f or 0) / equity))
        if not ranked:
            return sql, REFUSAL
        ranked.sort(key=lambda item: item[1], reverse=True)
        direction = params.get("direction", "high")
        if direction == "all":
            parts = [f"{asset} {rate * 100:.2f}%" for asset, rate in ranked]
            return sql, "Forecast return by asset: " + ", ".join(parts) + "."
        asset, rate = ranked[-1] if direction == "low" else ranked[0]
        label = "lowest" if direction == "low" else "highest"
        return sql, f"The {label} forecast return is {asset} at {rate * 100:.2f}%."
    if sql_id == "watchlist":
        sql = (
            "SELECT h.asset_id, h.country, h.sector, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Actual' THEN amount END) AS ytd_actual, "
            "SUM(CASE WHEN time_view = 'YTD' AND scenario = 'Budget' THEN amount END) AS ytd_budget, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Forecast' THEN amount END) AS annual_forecast, "
            "SUM(CASE WHEN time_view = 'Annual' AND scenario = 'Budget' THEN amount END) AS annual_budget "
            "FROM kpis k JOIN hierarchy h ON h.asset_id = k.asset_id "
            "WHERE k.metric = 'Net Income' "
            "GROUP BY h.asset_id, h.country, h.sector "
            "HAVING ytd_actual < ytd_budget AND annual_forecast < annual_budget "
            "ORDER BY (annual_forecast - annual_budget)"
        )
        frame = _run(sql)
        if frame.empty:
            return sql, "No asset is behind budget on both YTD and the annual forecast."
        names = ", ".join(
            f"{row.asset_id} ({row.country}, {row.sector})" for row in frame.itertuples(index=False)
        )
        return sql, f"These assets are behind on both YTD and the annual forecast: {names}."
    if sql_id == "statement_total":
        where = []
        bind: dict = {}
        for key in ("asset_id", "region", "country", "sector"):
            if params.get(key):
                where.append(f"h.{key} = :{key}")
                bind[key] = params[key]
        scope = " AND ".join(where) if where else "1 = 1"
        sql = (
            "SELECT "
            "SUM(CASE WHEN k.time_view = 'YTD' AND k.scenario = 'Actual' THEN k.amount END) AS ytd_actual, "
            "SUM(CASE WHEN k.time_view = 'YTD' AND k.scenario = 'Budget' THEN k.amount END) AS ytd_budget, "
            "SUM(CASE WHEN k.time_view = 'Annual' AND k.scenario = 'Forecast' THEN k.amount END) AS annual_forecast, "
            "SUM(CASE WHEN k.time_view = 'Annual' AND k.scenario = 'Budget' THEN k.amount END) AS annual_budget "
            "FROM kpis k JOIN hierarchy h ON h.asset_id = k.asset_id "
            f"WHERE {scope}"
        )
        frame = _run(sql, bind)
        row = frame.iloc[0]
        actual = float(row["ytd_actual"] or 0)
        budget = float(row["ytd_budget"] or 0)
        forecast = float(row["annual_forecast"] or 0)
        annual = float(row["annual_budget"] or 0)
        label = params.get("asset_id") or params.get("country") or params.get("sector") or params.get("region") or "Portfolio"
        return sql, (
            f"{label} income statement total: YTD actual {_money(actual)} vs YTD budget {_money(budget)} "
            f"(YTD Var % {_pct(variance_pct(actual, budget))}), and annual forecast {_money(forecast)} "
            f"vs annual budget {_money(annual)} (Annual Var % {_pct(variance_pct(forecast, annual))})."
        )
    if sql_id == "largest_miss":
        sql = (
            "SELECT metric, "
            "SUM(CASE WHEN scenario = 'Forecast' THEN amount END) AS forecast, "
            "SUM(CASE WHEN scenario = 'Budget' THEN amount END) AS budget "
            "FROM kpis WHERE time_view = 'Annual' "
            "GROUP BY metric "
            "ORDER BY (forecast - budget) ASC LIMIT 1"
        )
        frame = _run(sql)
        row = frame.iloc[0]
        gap = float(row["forecast"]) - float(row["budget"])
        return sql, (
            f"The largest annual dollar gap is {row['metric']}: forecast {_money(float(row['forecast']))} "
            f"vs budget {_money(float(row['budget']))}, a variance of {_money(gap)} "
            f"({_pct(variance_pct(float(row['forecast']), float(row['budget'])))})."
        )
    if sql_id == "equity_total":
        sql = (
            "SELECT "
            "SUM(CASE WHEN attribution_category = 'Opening' THEN bridge END) AS opening, "
            "SUM(bridge) AS total "
            "FROM equity_bridge WHERE scenario = :scenario"
        )
        frame = _run(sql, params)
        if frame["opening"].iloc[0] is None:
            return sql, REFUSAL
        return sql, (
            f"{params['scenario']} opening equity is {_money(float(frame['opening'].iloc[0]))} "
            f"and the total is {_money(float(frame['total'].iloc[0]))}."
        )
    if sql_id == "equity_category":
        sql = (
            "SELECT COALESCE(SUM(bridge), 0) AS amount FROM equity_bridge "
            "WHERE scenario = :scenario AND attribution_category = :category"
        )
        query_params = {"scenario": params["scenario"], "category": params["category"]}
        if params.get("region"):
            sql += " AND region = :region"
            query_params["region"] = params["region"]
        frame = _run(sql, query_params)
        where = params.get("region", "all regions")
        return sql, (
            f"{params['scenario']} {params['category']} for {where} is {_money(float(frame['amount'].iloc[0]))}."
        )
    if sql_id == "aum":
        sql = (
            "SELECT scenario, SUM(amount) AS amount FROM bs_by_region "
            "WHERE category IN ('Equity', 'Debt', '3rd Party') GROUP BY scenario"
        )
        frame = _run(sql)
        parts = [f"{row.scenario} {_money(float(row.amount))}" for row in frame.itertuples(index=False)]
        return sql, "Assets under management, equity plus debt plus third party: " + "; ".join(parts) + "."
    return "", REFUSAL


def answer(state: ChatState) -> ChatState:
    if state.get("sql_id") == "cte":
        try:
            frame = _run(state.get("sql_text", ""), state.get("params") or None)
        except Exception as exc:
            if (state.get("meta") or {}).get("shape") == "raw":
                return {"answer": str(exc), "sql_text": state.get("sql_text", "")}
            return {"answer": REFUSAL, "sql_text": state.get("sql_text", "")}
        return {"answer": speak_result(state.get("meta") or {}, frame), "sql_text": state.get("sql_text", "")}
    tables = _TABLES.get() or {}
    params = state.get("params") or {}
    if params.get("asset_id") and params["asset_id"] not in set(tables["hierarchy"]["asset_id"]):
        return {"answer": REFUSAL, "sql_text": ""}
    sql_text, spoken = _speak(state.get("sql_id", ""), params)
    return {"answer": spoken, "sql_text": sql_text}


def refuse(state: ChatState) -> ChatState:
    return {"answer": REFUSAL, "sql_text": ""}


def _route(state: ChatState) -> str:
    if state.get("route") in {"sql", "saved"}:
        return "answer"
    return "refuse"


def build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("prepare", prepare)
    graph.add_node("answer", answer)
    graph.add_node("refuse", refuse)
    graph.add_edge(START, "prepare")
    graph.add_conditional_edges("prepare", _route, {"answer": "answer", "refuse": "refuse"})
    graph.add_edge("answer", END)
    graph.add_edge("refuse", END)
    return graph.compile()


_APP = None


def ask(question: str) -> str:
    if not question.strip():
        return REFUSAL
    global _APP
    if _APP is None:
        _APP = build_graph()
    token = _TABLES.set(load_tables())
    try:
        result = _APP.invoke({"question": question})
    finally:
        _TABLES.reset(token)
    return result.get("answer") or REFUSAL
