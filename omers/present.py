"""Charts and table formatting shared by the dashboard pages."""

from __future__ import annotations

import math

import altair as alt
import pandas as pd

from omers.metrics import AUM_CATEGORIES, SCENARIO_ORDER

NAVY = "#0B3A5B"
GREEN = "#107C10"
RED = "#A4262C"
SECTOR_COLORS = ["#0B3A5B", "#118DFF", "#038387", "#CA5010", "#8764B8"]


def variance_card(column, gap_points: float | None) -> None:
    """Variance KPI: red when the gap is negative, dark blue when it is positive."""
    if gap_points is None:
        text = "n/a"
        color = "#252423"
    elif gap_points < 0:
        text = f"{gap_points:+.2f} pp"
        color = RED
    else:
        text = f"{gap_points:+.2f} pp"
        color = NAVY
    column.markdown(
        f"""
        <style>
        div[data-testid="stElementContainer"]:has(.variance-tone) {{
          display: none !important;
        }}
        div[data-testid="stColumn"]:has(.variance-tone) [data-testid="stMetricValue"],
        div[data-testid="stColumn"]:has(.variance-tone) [data-testid="stMetricValue"] * {{
          color: {color} !important;
        }}
        </style>
        <span class="variance-tone"></span>
        """,
        unsafe_allow_html=True,
    )
    column.metric("Variance", text)


def millions(frame: pd.DataFrame) -> pd.DataFrame:
    show = frame.copy()
    money = ["YTD Actual", "YTD Budget", "Annual Budget", "Annual Forecast"]
    for col in money:
        show[col] = show[col] / 1_000_000
    show["YTD Var %"] = pd.to_numeric(show["YTD Var %"], errors="coerce") * 100
    show["Annual Var %"] = pd.to_numeric(show["Annual Var %"], errors="coerce") * 100
    columns = ["Metric", *money[:2], "YTD Var %", *money[2:], "Annual Var %"]
    styled = show[columns].style.format(
        {
            "YTD Actual": "{:,.2f}",
            "YTD Budget": "{:,.2f}",
            "Annual Budget": "{:,.2f}",
            "Annual Forecast": "{:,.2f}",
            "YTD Var %": "{:+.2f}%",
            "Annual Var %": "{:+.2f}%",
        },
        na_rep="0.00%",
    )
    styled = styled.apply(_paint_variance, axis=1)
    return styled


def _paint_variance(row: pd.Series) -> list[str]:
    styles = ["font-weight: 600" if row["Metric"] == "Total" else ""] * len(row)
    for name in ("YTD Var %", "Annual Var %"):
        value = row[name]
        weight = "font-weight: 600"
        if pd.notna(value) and value > 0:
            styles[row.index.get_loc(name)] = f"color: {GREEN}; {weight}"
        elif pd.notna(value) and value < 0:
            styles[row.index.get_loc(name)] = f"color: {RED}; {weight}"
    return styles


def _arc(start: float, end: float, radius: float, steps: int = 80) -> pd.DataFrame:
    angles = [math.pi * (1 - start + (start - end) * i / steps) for i in range(steps + 1)]
    return pd.DataFrame(
        {
            "x": [radius * math.cos(angle) for angle in angles],
            "y": [radius * math.sin(angle) for angle in angles],
            "order": list(range(steps + 1)),
        }
    )


def _ray(fraction: float, inner: float, outer: float) -> pd.DataFrame:
    angle = math.pi * (1 - fraction)
    return pd.DataFrame(
        {
            "x": [inner * math.cos(angle), outer * math.cos(angle)],
            "y": [inner * math.sin(angle), outer * math.sin(angle)],
            "order": [0, 1],
        }
    )


def _gauge_kpis(forecast: float | None, budget: float | None) -> dict[str, str]:
    """Tooltip text that matches the three return cards above the gauge."""
    if forecast is None or budget is None:
        variance = "n/a"
    else:
        variance = f"{(float(forecast) - float(budget)) * 100:+.2f} pp"
    return {
        "Forecast return": "n/a" if forecast is None else f"{float(forecast) * 100:.2f}%",
        "Budget return": "n/a" if budget is None else f"{float(budget) * 100:.2f}%",
        "Variance": variance,
    }


def _with_kpis(frame: pd.DataFrame, kpis: dict[str, str]) -> pd.DataFrame:
    tagged = frame.copy()
    for name, text in kpis.items():
        tagged[name] = text
    return tagged


def gauge(forecast: float | None, budget: float | None) -> alt.LayerChart:
    """Semicircle from 0% to 25%. Navy arc is the forecast return. Red tick is the budget return."""
    vmax = 0.25
    value = 0.0 if forecast is None else float(forecast)
    fraction = min(max(value, 0.0), vmax) / vmax
    x_scale = alt.Scale(domain=[-1.75, 1.75])
    y_scale = alt.Scale(domain=[-0.55, 1.65])
    kpis = _gauge_kpis(forecast, budget)
    tip = [
        alt.Tooltip("Forecast return:N", title="Forecast return"),
        alt.Tooltip("Budget return:N", title="Budget return"),
        alt.Tooltip("Variance:N", title="Variance"),
    ]

    def ring(frame: pd.DataFrame, color: str, width: int) -> alt.Chart:
        return (
            alt.Chart(_with_kpis(frame, kpis))
            .mark_line(color=color, strokeWidth=width, strokeCap="round")
            .encode(
                x=alt.X("x:Q", scale=x_scale, axis=None),
                y=alt.Y("y:Q", scale=y_scale, axis=None),
                order="order:Q",
                tooltip=tip,
            )
        )

    layers: list[alt.Chart] = [
        ring(_arc(0.0, 1.0, 1.0), "#E1DFDD", 18),
        ring(_arc(0.0, fraction, 1.0), NAVY, 18),
        ring(_ray(fraction, 0.0, 0.96), "#252423", 3),
    ]
    if budget is not None:
        layers.append(ring(_ray(min(max(float(budget), 0.0), vmax) / vmax, 0.82, 1.18), RED, 3))

    ticks = []
    for percent in range(0, 26):
        point = min(percent / 100, vmax) / vmax
        angle = math.pi * (1 - point)
        outer = 1.22 if percent % 5 == 0 else 1.12
        ticks.append(
            {
                "x": outer * math.cos(angle),
                "y": outer * math.sin(angle),
                "x2": 1.08 * math.cos(angle),
                "y2": 1.08 * math.sin(angle),
                **kpis,
            }
        )
    tick_chart = (
        alt.Chart(pd.DataFrame(ticks))
        .mark_rule(color="#605E5C", strokeWidth=1)
        .encode(
            x=alt.X("x:Q", scale=x_scale, axis=None),
            x2="x2:Q",
            y=alt.Y("y:Q", scale=y_scale, axis=None),
            y2="y2:Q",
            tooltip=tip,
        )
    )
    labels = []
    for percent in range(0, 26, 5):
        point = (percent / 100) / vmax
        angle = math.pi * (1 - point)
        y = 1.48 * math.sin(angle)
        if percent in (0, 25):
            y -= 0.16
        labels.append({"x": 1.48 * math.cos(angle), "y": y, "label": f"{percent:.2f}%", **kpis})
    label_chart = (
        alt.Chart(pd.DataFrame(labels))
        .mark_text(fontSize=11, color="#605E5C")
        .encode(
            x=alt.X("x:Q", scale=x_scale, axis=None),
            y=alt.Y("y:Q", scale=y_scale, axis=None),
            text="label:N",
            tooltip=tip,
        )
    )
    callout = alt.Chart(
        _with_kpis(pd.DataFrame({"x": [0], "y": [-0.28], "label": [f"{value * 100:.2f}%"]}), kpis)
    ).mark_text(fontSize=28, fontWeight=600, color="#252423").encode(
        x=alt.X("x:Q", scale=x_scale, axis=None),
        y=alt.Y("y:Q", scale=y_scale, axis=None),
        text="label:N",
        tooltip=tip,
    )
    note = "Target" if budget is None else f"Target {budget * 100:.2f}%"
    budget_label = alt.Chart(
        _with_kpis(pd.DataFrame({"x": [0], "y": [-0.48], "label": [note]}), kpis)
    ).mark_text(fontSize=13, color=RED).encode(
        x=alt.X("x:Q", scale=x_scale, axis=None),
        y=alt.Y("y:Q", scale=y_scale, axis=None),
        text="label:N",
        tooltip=tip,
    )
    # Width and height keep one data unit the same size on both axes, so the needle meets the arc.
    return alt.layer(tick_chart, *layers, label_chart, callout, budget_label).properties(width=560, height=380)


def _billions(value: float) -> str:
    return f"${value / 1_000_000_000:.2f}bn"


def _millions_label(value: float) -> str:
    return f"${value / 1_000_000:.2f}M"


def aum_chart(frame: pd.DataFrame) -> alt.Chart:
    sort_map = {name: index for index, name in enumerate(AUM_CATEGORIES)}
    data = frame.copy()
    if data.empty:
        return alt.Chart(data).mark_bar()
    data["category_order"] = data["category"].map(sort_map)
    data = data.sort_values(["scenario", "category_order"])
    data["cum"] = data.groupby("scenario", sort=False)["amount"].cumsum()
    data["y0"] = data["cum"] - data["amount"]
    data["mid"] = data["cum"] - data["amount"] / 2
    data["label"] = data["amount"].map(_billions)
    totals = data.groupby("scenario", as_index=False)["amount"].sum()
    totals["label"] = totals["amount"].map(_billions)
    y_scale = alt.Scale(domain=[0, float(totals["amount"].max()) * 1.16])
    x = alt.X("scenario:N", sort=SCENARIO_ORDER, title=None)
    bars = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=x,
            y=alt.Y("y0:Q", title=None, scale=y_scale, axis=alt.Axis(format="$.2s")),
            y2="cum:Q",
            color=alt.Color(
                "category:N",
                scale=alt.Scale(
                    domain=AUM_CATEGORIES,
                    range=[NAVY, "#00B7C3", "#CA8A04"],
                ),
                title=None,
            ),
            tooltip=["scenario", "category", alt.Tooltip("label:N", title="Amount")],
        )
    )
    dark = data[data["category"] != "3rd Party"]
    gold = data[data["category"] == "3rd Party"]
    layers: list[alt.Chart] = [bars]
    if not dark.empty:
        layers.append(
            alt.Chart(dark)
            .mark_text(color="white", fontSize=11, fontWeight=600)
            .encode(x=x, y=alt.Y("mid:Q", scale=y_scale, axis=None), text="label:N")
        )
    if not gold.empty:
        layers.append(
            alt.Chart(gold)
            .mark_text(color="#252423", fontSize=11, fontWeight=600)
            .encode(x=x, y=alt.Y("mid:Q", scale=y_scale, axis=None), text="label:N")
        )
    layers.append(
        alt.Chart(totals)
        .mark_text(dy=-14, fontSize=13, fontWeight=700, color=NAVY)
        .encode(x=x, y=alt.Y("amount:Q", scale=y_scale, axis=None), text="label:N")
    )
    return alt.layer(*layers).properties(height=280)


def sector_chart(frame: pd.DataFrame) -> alt.Chart:
    data = frame.dropna(subset=["share"]).copy()
    if data.empty:
        return alt.Chart(data).mark_bar()
    data = data.sort_values(["scenario", "sector"])
    data["label"] = (data["share"] * 100).map(lambda value: f"{value:.2f}%")
    data = data[data["label"] != "0.00%"].copy()
    if data.empty:
        return alt.Chart(data).mark_bar()
    data["cum"] = data.groupby("scenario", sort=False)["share"].cumsum()
    data["y0"] = data["cum"] - data["share"]
    data["mid"] = data["cum"] - data["share"] / 2
    y_scale = alt.Scale(domain=[0, 1])
    x = alt.X("scenario:N", sort=SCENARIO_ORDER, title=None, axis=alt.Axis(labelAngle=0, labelLimit=120))
    bars = (
        alt.Chart(data)
        .mark_bar(size=78)
        .encode(
            x=x,
            y=alt.Y("y0:Q", title=None, scale=y_scale, axis=alt.Axis(format=".0%", values=[0, 0.5, 1])),
            y2="cum:Q",
            color=alt.Color(
                "sector:N",
                scale=alt.Scale(range=SECTOR_COLORS),
                title=None,
                legend=alt.Legend(orient="bottom", columns=3, labelLimit=140),
            ),
            tooltip=["scenario", "sector", alt.Tooltip("label:N", title="Share")],
        )
    )
    inside = data[data["share"] >= 0.08]
    outside = data[data["share"] < 0.08].copy()
    layers: list[alt.Chart] = [bars]
    if not inside.empty:
        layers.append(
            alt.Chart(inside)
            .mark_text(color="white", fontSize=12, fontWeight=600)
            .encode(x=x, y=alt.Y("mid:Q", scale=y_scale, axis=None), text="label:N")
        )
    if not outside.empty:
        ink = dict(zip(sorted(data["sector"].unique()), SECTOR_COLORS))
        for sector, part in outside.groupby("sector"):
            layers.append(
                alt.Chart(part)
                .mark_text(align="left", dx=44, fontSize=12, fontWeight=600, color=ink.get(sector, "#252423"))
                .encode(x=x, y=alt.Y("mid:Q", scale=y_scale, axis=None), text="label:N")
            )
    return alt.layer(*layers).properties(height=460)


def return_chart(frame: pd.DataFrame) -> alt.Chart:
    data = frame.dropna(subset=["forecast_return"]).copy()
    if data.empty:
        return alt.Chart(data).mark_bar()
    data["label"] = (data["forecast_return"] * 100).map(lambda value: f"{value:.2f}%")
    peak = float(data["forecast_return"].max())
    x_scale = alt.Scale(domain=[0, peak * 1.32 if peak else 0.01])
    y = alt.Y("asset_id:N", sort="-x", title=None)
    bars = (
        alt.Chart(data)
        .mark_bar(color=NAVY)
        .encode(
            y=y,
            x=alt.X("forecast_return:Q", title=None, scale=x_scale, axis=alt.Axis(format=".2%")),
            tooltip=["asset_id", alt.Tooltip("label:N", title="Forecast return")],
        )
    )
    text = (
        alt.Chart(data)
        .mark_text(align="left", dx=6, fontSize=12, fontWeight=600, color="#252423")
        .encode(
            y=y,
            x=alt.X("forecast_return:Q", scale=x_scale, axis=None),
            text="label:N",
        )
    )
    return (bars + text).properties(height=280)


def mtm_chart(frame: pd.DataFrame) -> alt.Chart:
    data = frame.copy()
    if data.empty:
        return alt.Chart(data).mark_bar()
    data["label"] = data["amount"].map(_millions_label)
    data = data[data["label"] != "$0.00M"].copy()
    if data.empty:
        return alt.Chart(data).mark_bar()
    line_order = ["MTM Assets", "MTM Debt", "NOI"]
    data["line"] = pd.Categorical(data["line"], line_order, ordered=True)
    data = data.sort_values(["asset_id", "line"])
    low = float(min(0.0, data["amount"].min()))
    high = float(max(0.0, data["amount"].max()))
    x_scale = alt.Scale(domain=[low - max(abs(low), 1.0) * 1.05, high + max(high, 1.0) * 0.58])
    labeled = data
    y = alt.Y("asset_id:N", title=None)
    offset = alt.YOffset("line:N", sort=line_order)
    color = alt.Color(
        "line:N",
        scale=alt.Scale(
            domain=line_order,
            range=["#CA8A04", RED, "#038387"],
        ),
        title=None,
        legend=alt.Legend(orient="top", columns=1, labelLimit=140),
        sort=line_order,
    )
    bars = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            y=y,
            x=alt.X("amount:Q", title=None, scale=x_scale, axis=alt.Axis(format="$.2s")),
            color=color,
            yOffset=offset,
            tooltip=["asset_id", "line", alt.Tooltip("label:N", title="Amount")],
        )
    )
    layers: list[alt.Chart] = [bars]
    positive = labeled[labeled["amount"] > 0]
    negative = labeled[labeled["amount"] < 0]
    if not positive.empty:
        layers.append(
            alt.Chart(positive)
            .mark_text(align="left", dx=4, fontSize=11, color="#252423")
            .encode(
                y=y,
                x=alt.X("amount:Q", scale=x_scale, axis=None),
                yOffset=offset,
                text="label:N",
            )
        )
    if not negative.empty:
        layers.append(
            alt.Chart(negative)
            .mark_text(align="right", dx=-4, fontSize=11, color="#252423")
            .encode(
                y=y,
                x=alt.X("amount:Q", scale=x_scale, axis=None),
                yOffset=offset,
                text="label:N",
            )
        )
    return alt.layer(*layers).properties(height=380)


def waterfall_chart(steps: pd.DataFrame) -> alt.Chart:
    data = steps.copy()
    data["low"] = data[["start", "end"]].min(axis=1)
    data["high"] = data[["start", "end"]].max(axis=1)

    def shade(row: pd.Series) -> str:
        if row["value"] < 0:
            return "down"
        if row["kind"] == "total":
            return "total"
        if row["kind"] == "opening":
            return "opening"
        return "up"

    data["shade"] = data.apply(shade, axis=1)
    data["label"] = data["value"].map(_billions)
    data["ink"] = data["value"].map(lambda value: RED if value < 0 else "#252423")
    order = data["category"].tolist()
    ymax = float(data["high"].max())
    ymin = min(0.0, float(data["low"].min()))
    y_scale = alt.Scale(domain=[ymin, ymax * 1.14 if ymax else 1.0])
    x = alt.X("category:N", sort=order, title=None)
    bars = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=x,
            y=alt.Y("low:Q", title=None, scale=y_scale, axis=alt.Axis(format="$.2s")),
            y2="high:Q",
            color=alt.Color(
                "shade:N",
                scale=alt.Scale(
                    domain=["opening", "up", "down", "total"],
                    range=[GREEN, GREEN, RED, NAVY],
                ),
                legend=None,
            ),
            tooltip=["category", alt.Tooltip("label:N", title="Amount")],
        )
    )
    text_layers = []
    for ink, part in data.groupby("ink", sort=False):
        text_layers.append(
            alt.Chart(part)
            .mark_text(dy=-10, fontSize=11, fontWeight=600, color=ink)
            .encode(x=x, y=alt.Y("high:Q", scale=y_scale, axis=None), text="label:N")
        )
    return alt.layer(bars, *text_layers).properties(height=420)
