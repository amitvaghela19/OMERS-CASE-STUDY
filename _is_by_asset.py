from omers.metrics import income_statement
from omers.store import load_tables

tables = load_tables()
kpis = tables["kpis"]
money = ["YTD Actual", "YTD Budget", "Annual Budget", "Annual Forecast"]
print("per asset component sum vs net income")
for asset in sorted(kpis["asset_id"].unique()):
    statement = income_statement(kpis, {asset})
    lines = statement[~statement["Metric"].isin(["Net Income", "Total"])]
    net = statement[statement["Metric"] == "Net Income"].iloc[0]
    bad = []
    for col in money:
        diff = float(lines[col].sum()) - float(net[col])
        if abs(diff) > 0.5:
            bad.append(f"{col} diff {diff}")
    print(asset, "OK" if not bad else bad)

print("\nmetrics", sorted(kpis["metric"].unique()))
print("scenarios", sorted(kpis["scenario"].unique()), sorted(kpis["time_view"].unique()))
