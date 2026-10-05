"""Validate the planned Power Query grain against Test Case.xlsx."""
from collections import defaultdict
from pathlib import Path

import openpyxl

wb = openpyxl.load_workbook(Path(__file__).with_name("Test Case.xlsx"), data_only=True)
print("sheets", wb.sheetnames)

rules = [
    ("-YTD Variance", "YTD", "Variance"),
    ("-YTD Budget", "YTD", "Budget"),
    ("-Forecast", "Annual", "Forecast"),
    ("-Budget", "Annual", "Budget"),
    ("-Variance", "Annual", "Variance"),
    ("-Actual", "YTD", "Actual"),
]


def parse(attr: str):
    for suffix, view, scenario in rules:
        if attr.endswith(suffix):
            return attr[: -len(suffix)], view, scenario
    raise ValueError(attr)


ws = wb["KPI's"]
headers = [c.value for c in ws[17]]
assert headers[0] == "Asset ID"
agg = defaultdict(float)
for row in ws.iter_rows(min_row=18, values_only=True):
    aid = row[0]
    if not aid:
        continue
    for i, h in enumerate(headers):
        if i < 2 or not h or row[i] is None:
            continue
        agg[(aid, str(h))] += float(row[i])

parsed = defaultdict(float)
metrics = set()
for (aid, col), val in agg.items():
    metric, view, scenario = parse(col)
    metrics.add(metric)
    if scenario == "Variance":
        continue
    parsed[(aid, metric, view, scenario)] += val

print("kpi assets", len({k[0] for k in parsed}))
print("kpi metrics", sorted(metrics))
print("kpi fact rows", len(parsed))
print("kpi metric count", len(metrics))

ws = wb["BS by Region"]
bs = defaultdict(lambda: [0.0, 0.0, 0.0])
for cat, aid, ytd, fcst, op, srt in ws.iter_rows(min_row=2, values_only=True):
    if not cat or cat == "AUM":
        continue
    b = bs[(aid, cat, srt)]
    b[0] += round(float(ytd or 0), 2)
    b[1] += round(float(fcst or 0), 2)
    b[2] += round(float(op or 0), 2)
# group then round is closer to PQ (sum raw then round). Recompute properly.
bs = defaultdict(lambda: [0.0, 0.0, 0.0])
for cat, aid, ytd, fcst, op, srt in ws.iter_rows(min_row=2, values_only=True):
    if not cat or cat == "AUM":
        continue
    b = bs[(aid, cat)]
    b[0] += float(ytd or 0)
    b[1] += float(fcst or 0)
    b[2] += float(op or 0)
rows = 0
for key, vals in bs.items():
    for v in vals:
        rows += 1
print("bs grouped keys", len(bs), "unpivoted", rows)

hier = [r[3] for r in wb["Hierarchy"].iter_rows(min_row=2, values_only=True) if r[3]]
print("hierarchy", len(hier), hier)
print("bridge rows", wb["Equity Bridge"].max_row - 1)
