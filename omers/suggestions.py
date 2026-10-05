"""Ten suggested questions drawn from the loaded workbook."""

from __future__ import annotations

import random

import pandas as pd

TAGS = (
    "asset_income",
    "asset_return",
    "asset_noi",
    "asset_variance",
    "asset_equity",
    "statement",
    "region_return",
    "region_list",
    "region_capex",
    "region_count",
    "country_noi",
    "sector_return",
    "rank_high",
    "rank_low",
    "rank_all",
    "watch",
    "miss",
    "aum",
    "opening",
    "total",
)


def catalog(tables: dict[str, pd.DataFrame]) -> list[tuple[str, str]]:
    hierarchy = tables["hierarchy"]
    assets = hierarchy["asset_id"].dropna().unique().tolist()
    regions = hierarchy["region"].dropna().unique().tolist()
    countries = hierarchy["country"].dropna().unique().tolist()
    sectors = hierarchy["sector"].dropna().unique().tolist()
    rows: list[tuple[str, str]] = []
    for asset in assets:
        rows.extend(
            [
                ("asset_income", f"What is {asset} annual forecast net income?"),
                ("asset_return", f"What is the forecast return for {asset}?"),
                ("asset_noi", f"What is {asset} YTD actual NOI?"),
                ("asset_variance", f"How does {asset} net income compare with budget?"),
                ("asset_equity", f"What is {asset} annual forecast equity?"),
                ("statement", f"Show the income statement for {asset}"),
            ]
        )
    rows.extend(
        [
            ("statement", "What is the income statement total?"),
            ("statement", "What is the portfolio YTD variance percent?"),
            ("statement", "What is the portfolio annual variance percent?"),
        ]
    )
    for region in regions:
        rows.extend(
            [
                ("region_return", f"How does the {region} forecast return compare with budget?"),
                ("region_list", f"List the assets in {region}"),
                ("region_capex", f"What is December 2019 capex for {region}?"),
                ("region_count", f"How many assets are in {region}?"),
            ]
        )
    for country in countries:
        rows.append(("country_noi", f"What is {country} annual forecast NOI?"))
    for sector in sectors:
        rows.append(("sector_return", f"What is the forecast return for {sector}?"))
    rows.extend(
        [
            ("rank_high", "Which asset has the highest forecast return?"),
            ("rank_low", "Which asset has the lowest forecast return?"),
            ("rank_all", "Rank the assets by forecast return."),
            ("watch", "Which assets are behind on both YTD and the annual forecast?"),
            ("miss", "What is the largest annual forecast versus budget gap?"),
            ("aum", "What is assets under management by scenario?"),
            ("opening", "What is December 2019 opening equity?"),
            ("total", "What is December 2019 total equity?"),
        ]
    )
    return rows


def pick_suggestions(
    tables: dict[str, pd.DataFrame],
    count: int = 10,
    avoid: set[str] | None = None,
) -> list[str]:
    blocked = set(avoid or ())
    grouped: dict[str, list[str]] = {tag: [] for tag in TAGS}
    for tag, question in catalog(tables):
        if question not in blocked:
            grouped.setdefault(tag, []).append(question)
    tags = [tag for tag in TAGS if grouped.get(tag)]
    random.shuffle(tags)
    chosen: list[str] = []
    for tag in tags:
        choice = random.choice(grouped[tag])
        chosen.append(choice)
        if len(chosen) == count:
            return chosen
    leftovers = [question for tag in tags for question in grouped[tag] if question not in chosen]
    random.shuffle(leftovers)
    chosen.extend(leftovers[: count - len(chosen)])
    return chosen
