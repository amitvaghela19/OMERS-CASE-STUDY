# Model

Load only these four queries from `powerquery\`. Do not load Instructions, Returns, or Sheet1.

Turn off **Autodetect new relationships** before refresh (File → Options → Current file → Data load).

## Tables after refresh

| Query | Role | Rows |
|---|---|---|
| Hierarchy | Only dimension. Key = `Asset ID` | 6 |
| BS by Region | Fact. Asset ID + Category + Scenario | 72 |
| KPI's | Fact. Asset ID + Metric + TimeView + Scenario | 264 |
| Equity Bridge | Disconnected fact. Region + Scenario + Attribution Category | 117 |

`BS by Region` has no AUM category. AUM is the `AUM` measure (Equity + Debt + 3rd Party).

## Relationships (exactly two)

Both single direction, one-to-many, from Hierarchy to the fact.

| From | To | Cardinality | Filter |
|---|---|---|---|
| Hierarchy[Asset ID] | BS by Region[Asset ID] | 1:* | Single |
| Hierarchy[Asset ID] | KPI's[Asset ID] | 1:* | Single |

Do not relate BS by Region to KPI's. Do not relate Equity Bridge to Hierarchy on Region (North America is three assets, so that join is many-to-many). The waterfall uses `Bridge Amount` (`TREATAS`).

## Sort by column

| Column | Sort by |
|---|---|
| BS by Region[Category] | Category Sort |
| BS by Region[Scenario] | Scenario Sort |
| KPI's[Metric] | Metric Sort |
| Equity Bridge[Attribution Category] | Sort Order |
| Equity Bridge[Scenario] | Scenario Sort |

Category Sort is already Equity=1, Debt=2, Real Estate=3, 3rd Party=4.

## QA after refresh

- Distinct Hierarchy[Asset ID] = 6
- KPI's rows = 264 (6 assets × 11 metrics × 4 scenarios). No Variance rows.
- BS by Region rows = 72 (6 × 4 categories × 3 scenarios)
- BS Category does not contain AUM
- For each asset and scenario, Equity + Debt + 3rd Party equals the AUM rows you dropped, within cents
