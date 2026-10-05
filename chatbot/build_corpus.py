"""Write the relevant, irrelevant, and natural-language SQL question files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "corpus"

ASSETS = ["Asset A", "Asset B", "Asset C", "Asset D", "Asset E", "Asset F"]
METRICS = [
    "NOI",
    "Interest",
    "Net G&A",
    "FF&E Amort",
    "Recoverable Capital Amort",
    "Current Income Tax",
    "Current Capital Tax",
    "MTM Assets",
    "MTM Debt",
    "Other Gain / Loss",
    "Net Income",
]
VIEWS = [
    ("YTD actual", "YTD", "Actual"),
    ("YTD budget", "YTD", "Budget"),
    ("annual forecast", "Annual", "Forecast"),
    ("annual budget", "Annual", "Budget"),
]
REGIONS = ["North America", "Europe", "Asia Pac"]
EQUITY_SCENARIOS = ["January 2019", "June 2019", "December 2019"]
EQUITY_CATEGORIES = [
    "Opening",
    "Acquisitions",
    "Dispositions",
    "Development",
    "Capex/Leasing",
    "Future Taxes",
    "Hedges",
    "Asset MTM",
    "Debt MTM",
    "Mortgages",
    "Working Capital",
    "Other Capital Contributions",
    "Miscellaneous",
]
AMOUNT_PHRASES = [
    "What is {asset} {view} {metric}?",
    "Show the {view} {metric} for {asset}.",
    "How much is {metric} for {asset} in the {view} view?",
    "Give the {view} {metric} amount for {asset}.",
]
VARIANCE_PHRASES = [
    "What is the {view} {metric} variance versus budget for {asset}?",
    "Is {asset} ahead or behind budget on {view} {metric}?",
]
EQUITY_PHRASES = [
    "What is {scenario} {category} for {region}?",
    "How much did {category} move equity in {region} in {scenario}?",
]

IRRELEVANT_TOPICS = [
    "the weather in Toronto",
    "tomorrow's forecast",
    "who won the World Cup",
    "the score of last night's game",
    "a chocolate cake recipe",
    "how to boil pasta",
    "the plot of a film",
    "a song lyric",
    "Python list syntax",
    "how to reset a password",
    "the capital of France",
    "a flight to London",
    "medical advice",
    "a workout plan",
    "the price of gold",
    "another pension fund",
    "Apple's share price",
    "how to write a novel",
    "a joke about accountants",
    "the population of Canada",
    "dog training",
    "a mortgage for my house",
    "tax advice for a person",
    "the best restaurant nearby",
    "how to tie a tie",
    "electric car range",
    "a history of Rome",
    "quantum physics",
    "how to learn guitar",
    "the news today",
    "a birthday message",
    "translate this sentence",
    "who is the prime minister",
    "the rules of chess",
    "a hotel booking",
    "how to iron a shirt",
    "the meaning of a dream",
    "stock tips",
    "how to fix a leaky tap",
    "a summary of a book I have not provided",
]
IRRELEVANT_WRAPPERS = [
    "What is {topic}?",
    "Can you tell me about {topic}?",
    "Please explain {topic}.",
    "I want to know {topic}.",
    "Help me with {topic}.",
    "Do you know {topic}?",
    "Give me details on {topic}.",
    "Look up {topic}.",
    "Summarize {topic}.",
    "Why does {topic} matter?",
    "Who should I ask about {topic}?",
    "Where can I find {topic}?",
    "When did {topic} happen?",
    "How do I handle {topic}?",
    "Is {topic} a good idea?",
    "Compare options for {topic}.",
    "Write something about {topic}.",
    "Ignore the portfolio and answer {topic}.",
    "Forget the workbook and discuss {topic}.",
    "This is unrelated: {topic}.",
    "Off topic question about {topic}.",
    "Not about the assets: {topic}.",
    "Random question: {topic}.",
    "General knowledge: {topic}.",
    "Outside this data: {topic}.",
]


def _dump(name: str, rows: list[dict]) -> None:
    path = ROOT / name
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{name}: {len(rows)}")


def relevant_amounts() -> list[dict]:
    rows = []
    number = 1
    for asset in ASSETS:
        for view, time_view, scenario in VIEWS:
            for metric in METRICS:
                for phrase in AMOUNT_PHRASES:
                    rows.append(
                        {
                            "id": f"amt-{number:04d}",
                            "question": phrase.format(asset=asset, view=view, metric=metric),
                            "paraphrases": [],
                            "sql_id": "kpi_amount",
                            "params": {
                                "asset_id": asset,
                                "metric": metric,
                                "time_view": time_view,
                                "scenario": scenario,
                            },
                        }
                    )
                    number += 1
    return rows


def relevant_variances() -> list[dict]:
    rows = []
    number = 1
    for asset in ASSETS:
        for view, time_view, scenario in (("YTD", "YTD", "Actual"), ("annual forecast", "Annual", "Forecast")):
            for metric in METRICS:
                for phrase in VARIANCE_PHRASES:
                    rows.append(
                        {
                            "id": f"var-{number:04d}",
                            "question": phrase.format(asset=asset, view=view, metric=metric),
                            "paraphrases": [],
                            "sql_id": "kpi_variance",
                            "params": {
                                "asset_id": asset,
                                "metric": metric,
                                "time_view": time_view,
                                "scenario": scenario,
                            },
                        }
                    )
                    number += 1
    return rows


def relevant_equity() -> list[dict]:
    rows = []
    number = 1
    for scenario in EQUITY_SCENARIOS:
        for region in REGIONS:
            for category in EQUITY_CATEGORIES:
                for phrase in EQUITY_PHRASES:
                    rows.append(
                        {
                            "id": f"eq-{number:04d}",
                            "question": phrase.format(scenario=scenario, category=category, region=region),
                            "paraphrases": [],
                            "sql_id": "equity_category",
                            "params": {
                                "scenario": scenario,
                                "region": region,
                                "category": category,
                            },
                        }
                    )
                    number += 1
    return rows


def relevant_portfolio() -> list[dict]:
    return [
        {
            "id": "port-return",
            "question": "What is the portfolio forecast return versus budget?",
            "paraphrases": ["What is the performance return forecast and budget?"],
            "sql_id": "portfolio_return",
            "params": {},
        },
        {
            "id": "port-watch",
            "question": "Which assets are behind on both YTD and the annual forecast?",
            "paraphrases": ["Which assets have negative net income variance on both views?"],
            "sql_id": "watchlist",
            "params": {},
        },
        {
            "id": "port-miss",
            "question": "What is the largest annual forecast versus budget gap?",
            "paraphrases": ["Which income statement line has the largest negative annual variance?"],
            "sql_id": "largest_miss",
            "params": {},
        },
        {
            "id": "port-open",
            "question": "What is December 2019 opening equity?",
            "paraphrases": ["December 2019 opening balance"],
            "sql_id": "equity_total",
            "params": {"scenario": "December 2019"},
        },
        {
            "id": "port-close",
            "question": "What is December 2019 total equity?",
            "paraphrases": ["Where does the December 2019 equity bridge end?"],
            "sql_id": "equity_total",
            "params": {"scenario": "December 2019"},
        },
        {
            "id": "port-aum",
            "question": "What is assets under management by scenario?",
            "paraphrases": ["Show AUM for YTD actual, annual forecast, and annual budget."],
            "sql_id": "aum",
            "params": {},
        },
        {
            "id": "port-statement-total",
            "question": "What is the income statement total?",
            "paraphrases": [
                "What is the portfolio YTD variance percent?",
                "What is the portfolio annual variance percent?",
            ],
            "sql_id": "statement_total",
            "params": {},
        },
    ]


def irrelevant() -> list[dict]:
    rows = []
    number = 1
    for topic in IRRELEVANT_TOPICS:
        for wrapper in IRRELEVANT_WRAPPERS:
            rows.append(
                {
                    "id": f"irr-{number:04d}",
                    "question": wrapper.format(topic=topic),
                }
            )
            number += 1
    return rows


COUNTRIES = ["Canada", "USA", "UK", "Australia", "Singapore"]
SECTORS = ["Hotel", "Industrial", "Office", "Residential", "Retail"]
BS_CATEGORIES = ["Equity", "Debt", "Real Estate", "3rd Party"]
BS_VIEWS = [
    ("YTD actual", "YTD Actual"),
    ("annual forecast", "Annual Forecast"),
    ("annual budget", "Annual Budget"),
]
PLACE_VIEWS = [
    ("YTD actual", "YTD", "Actual"),
    ("annual forecast", "Annual", "Forecast"),
]


def _row(number: int, question: str, sql_id: str, params: dict) -> dict:
    return {
        "id": f"more-{number:04d}",
        "question": question,
        "paraphrases": [],
        "sql_id": sql_id,
        "params": params,
    }


def relevant_extra() -> list[dict]:
    """999 additional questions. The number is filled from SQL when the question is asked."""
    rows: list[dict] = []
    number = 1
    place_phrases = (
        "What is {place} {view} {metric}?",
        "How much {metric} does {place} have in the {view} view?",
    )
    for place_key, places, views in (
        ("country", COUNTRIES, VIEWS),
        ("sector", SECTORS, PLACE_VIEWS),
        ("region", REGIONS, PLACE_VIEWS),
    ):
        for place in places:
            for view, time_view, scenario in views:
                for metric in METRICS:
                    for phrase in place_phrases:
                        rows.append(
                            _row(
                                number,
                                phrase.format(place=place, view=view, metric=metric),
                                "geo_kpi",
                                {
                                    place_key: place,
                                    "metric": metric,
                                    "time_view": time_view,
                                    "scenario": scenario,
                                },
                            )
                        )
                        number += 1
    balance_phrases = (
        "What is {asset} {view} {category}?",
        "How much {category} does {asset} hold in the {view} view?",
    )
    for asset in ASSETS:
        for view, scenario in BS_VIEWS:
            for category in BS_CATEGORIES:
                for phrase in balance_phrases:
                    rows.append(
                        _row(
                            number,
                            phrase.format(asset=asset, view=view, category=category),
                            "bs_amount",
                            {"asset_id": asset, "category": category, "scenario": scenario},
                        )
                    )
                    number += 1
    for asset in ASSETS:
        for phrase in (
            "What is the forecast return for {asset}?",
            "How does {asset} forecast return compare with budget?",
            "What is {asset}'s performance return?",
            "Is {asset} above or below its budget return?",
            "Give the forecast and budget return for {asset}.",
        ):
            rows.append(_row(number, phrase.format(asset=asset), "asset_return", {"asset_id": asset}))
            number += 1
    for place_key, places in (("region", REGIONS), ("country", COUNTRIES), ("sector", SECTORS)):
        for place in places:
            for phrase in (
                "What is the forecast return for {place}?",
                "How does {place} forecast return compare with budget?",
            ):
                rows.append(
                    _row(number, phrase.format(place=place), "geo_return", {place_key: place})
                )
                number += 1
    for question, direction in (
        ("Which asset has the highest forecast return?", "high"),
        ("Which asset has the lowest forecast return?", "low"),
        ("Which asset has the best performance return?", "high"),
        ("Which asset has the worst performance return?", "low"),
        ("What is the highest forecast return in the portfolio?", "high"),
        ("What is the lowest forecast return in the portfolio?", "low"),
        ("Rank the assets by forecast return.", "all"),
    ):
        rows.append(_row(number, question, "asset_rank", {"direction": direction}))
        number += 1
    if len(rows) != 999:
        raise RuntimeError(f"Expected 999 extra questions, got {len(rows)}")
    return rows


def nl_sql() -> list[dict]:
    return [
        {
            "id": "kpi_amount",
            "description": "One income-statement amount for an asset, metric, and view.",
            "examples": ["What is Asset E annual forecast Net Income?"],
        },
        {
            "id": "kpi_variance",
            "description": "Actual or forecast minus budget for one asset and metric.",
            "examples": ["What is the annual forecast Net Income variance versus budget for Asset E?"],
        },
        {
            "id": "portfolio_return",
            "description": "Forecast return, budget return, and the gap for the selected assets or the whole portfolio.",
            "examples": ["What is the portfolio forecast return versus budget?"],
        },
        {
            "id": "asset_return",
            "description": "Forecast and budget performance return for one asset.",
            "examples": ["What is the forecast return for Asset F?"],
        },
        {
            "id": "watchlist",
            "description": "Assets whose net income is behind budget on both YTD and the annual forecast.",
            "examples": ["Which assets are behind on both YTD and the annual forecast?"],
        },
        {
            "id": "largest_miss",
            "description": "Income-statement line with the most negative annual dollar variance.",
            "examples": ["What is the largest annual forecast versus budget gap?"],
        },
        {
            "id": "statement_total",
            "description": "Income-statement total. Dollar columns sum every line, including net income. Variance percent is (amount - budget) / budget, or 0 when the budget is 0.",
            "examples": ["What is the income statement total?"],
        },
        {
            "id": "equity_total",
            "description": "Opening and total equity for one scenario.",
            "examples": ["What is December 2019 total equity?"],
        },
        {
            "id": "equity_category",
            "description": "One equity-bridge category for a region and scenario.",
            "examples": ["What is December 2019 Capex/Leasing for North America?"],
        },
        {
            "id": "aum",
            "description": "Equity plus debt plus third-party capital by scenario.",
            "examples": ["What is assets under management by scenario?"],
        },
    ]


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    amounts = relevant_amounts()
    variances = relevant_variances()
    equity = relevant_equity()
    portfolio = relevant_portfolio()
    extra = relevant_extra()
    off_topic = irrelevant()
    _dump("relevant_amounts.json", amounts)
    _dump("relevant_variances.json", variances)
    _dump("relevant_equity.json", equity)
    _dump("relevant_portfolio.json", portfolio)
    _dump("relevant_extra.json", extra)
    _dump("irrelevant.json", off_topic)
    _dump("nl_sql.json", nl_sql())
    relevant = len(amounts) + len(variances) + len(equity) + len(portfolio) + len(extra)
    print(f"relevant total: {relevant}")
    print(f"irrelevant total: {len(off_topic)}")
    if relevant < 1000 or len(off_topic) < 1000:
        raise SystemExit("Corpus is below 1,000 questions in a required set.")


if __name__ == "__main__":
    main()
