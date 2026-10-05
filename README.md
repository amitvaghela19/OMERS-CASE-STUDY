# OMERS portfolio dashboard

Local Streamlit app for the case-study workbook. It cleans `Test Case.xlsx` the same way as the Power Query files, stores the result in SQLite, and shows portfolio performance, equity movements, three findings, a logged SQL tab, and a chatbot. Every figure comes from that cleaned database.

The click-by-click Power BI build is in [BABYSTEPS.md](BABYSTEPS.md). The table layout is in [MODEL.md](MODEL.md).

## 1. What you need

- Python 3.11 or newer
- `Test Case.xlsx` in this folder
- The packages in `requirements.txt`: Streamlit, pandas, openpyxl, SQLAlchemy, LangGraph

No API key. The chatbot does not call a language model.

## 2. Start the app

From this folder:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open http://localhost:8501.

On the first launch the app looks for `data/omers.db`. If that database is already there, it uses it. If not, and `Test Case.xlsx` is in this folder, it cleans that file and builds the database. The sidebar then shows the row counts.

To load the original file again, click **Reload Test Case.xlsx**. To load another workbook with the same sheets and columns, use **Upload**. A bad file stays off the pages and the error is shown in the sidebar.

## 3. Cleaning steps

Only these sheets are loaded: **Hierarchy**, **BS by Region**, **KPI's**, **Equity Bridge**. Instructions, Returns, and Sheet1 are ignored.

1. **Hierarchy.** Keep Region, Country, Sector, and Asset ID. Trim text. Drop blank Asset IDs. One row per asset. Expected: 6 assets (A through F).
2. **Balance sheet.** Drop the AUM rows. AUM is calculated later as Equity + Debt + 3rd Party. Round amounts to cents. Sum rows that share an asset and category. Unpivot YTD Actual, Forecast, and Operating Plan into scenarios named YTD Actual, Annual Forecast, and Annual Budget. Expected: 72 rows.
3. **KPI's.** Skip the junk rows above the real header (the row that contains Asset ID and NOI). Drop Description. Sum rows that share an Asset ID, so Asset E is one asset. Unpivot each metric column into Metric, Time View, and Scenario. Drop the stored Variance columns. The dashboard calculates variance itself. Expected: 264 rows (6 assets × 11 metrics × 4 scenarios).
4. **Equity bridge.** Keep the region grain. Map Jan / Jun / Dec 2019 to January, June, and December 2019. This table is not joined to Hierarchy. Expected: 117 rows.

The cleaned tables are written to `data/omers.db` and `data/cleaned_workbook.xlsx`.

SQLite tables:

| Table | Grain |
|---|---|
| `hierarchy` | region, country, sector, asset_id |
| `bs_by_region` | asset, category, scenario, amount |
| `kpis` | asset, metric, time view, scenario, amount |
| `equity_bridge` | region, scenario, attribution category, bridge |

## 4. Use the pages

### Portfolio performance

1. Leave Region, Country, and Sector unselected to see the whole portfolio.
2. Select one or more tiles to limit the assets. The cards, gauge, income statement, and charts all use that cohort.
3. Click **Reset cohort** to clear every tile on this page.

With no tile selected:

| Card | Value |
|---|---|
| Forecast return | 6.42% |
| Budget return | 13.72% |
| Variance | −7.30 percentage points |

The gauge runs from 0% to 25%. The navy arc is the forecast return. The red tick is the budget return.

The income statement is in $ millions. Green means the variance percent is above zero. Red means it is below zero.

### Equity movements

1. Pick one scenario. The default is December 2019. Do not add January, June, and December together. That triples the opening balance to $39.00bn.
2. Pick All, or one region.
3. Click **Reset cohort** to return to All regions and December 2019.

December 2019, all regions: opening **$13.00bn**, total **$15.54bn**.

### Key findings

Three paragraphs computed from the cleaned tables: the return gap and the largest annual miss, the assets behind budget on both YTD and the annual forecast, and the December equity bridge.

### SQL

1. Type one `SELECT` or one `WITH` query.
2. Click **Run query**.
3. Read the result and the query log under it.

The runner rejects a second statement and any insert, update, delete, drop, alter, create, attach, detach, pragma, replace, vacuum, reindex, or grant. Each attempt is logged to `data/sql_query_log.csv` with the time, statement, status, row count or error, and duration.

### Chat

1. Read the 10 suggested questions, or type your own.
2. Click **Refresh** to replace the 10 with a different set drawn from the loaded workbook.
3. Click a suggestion to ask it.

Each answer is one read-only query, written as a `WITH` statement, against the cleaned database. A question that is not about this workbook gets exactly: `I don't know the answer, but I will get back to you.`

## 5. How the numbers are calculated

Performance return forecast = annual forecast Net Income / annual forecast Equity.

Performance return budget = annual budget Net Income / annual budget Equity.

Return variance, in percentage points = forecast return − budget return.

AUM = Equity + Debt + 3rd Party. Real Estate is gross asset value and is not part of AUM.

Income-statement variance percent, for each line and for the total:

- YTD Var % = (YTD actual − YTD budget) / YTD budget
- Annual Var % = (annual forecast − annual budget) / annual budget
- If the budget is zero, the variance percent is 0%

The income statement total adds every line in the column, including Net Income. The total variance percents use the formulas above on those column totals. They are not the sum of the line percents.

Expense lines are already signed negative in the workbook. The percent uses that signed budget, so a cost line can show a negative percent when the dollar gap is positive.

Equity total for one scenario = opening plus the bridge categories. Total is calculated. It is not a stored category.

## 6. Rebuild the chat question files

The question lists live in `chatbot/corpus/`. To write them again:

```bash
python chatbot/build_corpus.py
```

The files store questions, not answer numbers. Answers are calculated when the question is asked.

## 7. Checks after a reload

| Check | Expected |
|---|---|
| Hierarchy rows | 6 |
| Balance-sheet rows | 72 |
| KPI rows | 264 |
| Equity-bridge rows | 117 |
| Forecast return, no filters | 6.42% |
| Budget return, no filters | 13.72% |
| Return variance | −7.30 pp |
| Net Income YTD actual | $73.69 million |
| Income statement total, YTD actual | $147.38 million |
| Income statement total, YTD Var % | −66.09% |
| Income statement total, annual forecast | $261.11 million |
| Income statement total, Annual Var % | −52.56% |
| December 2019 opening, all regions | $13.00bn |
| December 2019 total, all regions | $15.54bn |
