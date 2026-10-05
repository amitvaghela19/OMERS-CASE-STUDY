# Baby steps: OMERS Power BI, start to finish

Do these in order. Do not skip a step. Do not load Instructions, Returns, or Sheet1. Do not create extra tables.

Files you will paste from this folder:

- `powerquery\Hierarchy.m`
- `powerquery\BS by Region.m`
- `powerquery\KPIs.m`
- `powerquery\Equity Bridge.m`
- `DAX_measures.dax`

When you are done you should have three pages, two relationships, and these checks:

| Check | Expected |
|---|---|
| Hierarchy rows | 6 |
| BS by Region rows | 72 |
| KPI's rows | 264 |
| Equity Bridge rows | 117 |
| Performance Return Forecast | 6.4% |
| Performance Return Budget | 13.7% |
| Variance | −7.3 pp |
| Relationships | exactly 2 |

---

## 0. Colors, legends, and rules (use these everywhere)

Page canvas (instruction 1), every page: `#F2F2F2`.

Visual cards sit on white `#FFFFFF` with a 1 px border `#E1DFDD`. No shadow. No rounded corners.

Text: Segoe UI. Titles `#605E5C`, 12 pt, bold. Numbers `#252423`.

**AUM stacked chart legend (Category).** Bottom. This order, because Category Sort is Equity, Debt, Real Estate, 3rd Party — Real Estate is filtered off this chart:

| Series | Color | Hex |
|---|---|---|
| Equity | Navy | `#0B3A5B` |
| Debt | Teal | `#00B7C3` |
| 3rd Party | Gold | `#CA8A04` |

**Sector 100% chart legend.** Bottom. Same color every time you show a sector:

| Sector | Hex |
|---|---|
| Industrial | `#0B3A5B` |
| Office | `#118DFF` |
| Retail | `#038387` |
| Hotel | `#CA5010` |
| Residential | `#8764B8` |

**NOI vs MTM legend.** Bottom:

| Series | Hex |
|---|---|
| NOI YTD Actual | `#038387` |
| MTM Assets YTD | `#CA8A04` |
| MTM Debt YTD | `#A4262C` |

**Variance icons.** Green `#107C10` when the number is above 0. Red `#A4262C` when it is below 0. Do not flip this for Interest or tax. Those amounts are already negative in the file, so a positive variance already means “better than budget.”

**Waterfall.** Increases `#107C10`. Decreases `#A4262C`. Totals `#0B3A5B`.

**Slicers.** Style = Tile. Header on. Orientation = Horizontal. Single select = Off, except the Scenario slicer on page 3 (Single select = On). Selected tile: background `#0B3A5B`, font white. Unselected tile: background `#FAF9F8`, font `#252423`, border `#E1DFDD`.

**Charts.** Legend at the bottom, not the right. Y-axis title on. X-axis title on. Horizontal gridlines only, color `#EDEBE9`. No gradient. No data labels on the two big stacked charts (the axis is enough). Data labels on for the return-by-asset bar and the waterfall.

**Display units.** AUM and waterfall: Billions, 2 decimals. Income statement matrix: Millions, 1 decimal. Return charts: Percentage.

---

## 1. Open a blank file and turn autodetect off

1. Open **Power BI Desktop**.
2. If a start screen appears, choose **Blank report**.
3. **File → Options and settings → Options**.
4. Left side, under **CURRENT FILE**, click **Data Load**.
5. Uncheck **Autodetect new relationships after data is loaded**.
6. Click **OK**.

If you leave this on, Power BI will join BS to KPI's on Asset ID and the numbers will be wrong.

---

## 2. Create the four queries with Advanced Editor

You will make four **Blank queries**, then replace each script. Do not use Get Data → Excel and tick every sheet.

### 2.1 Hierarchy

1. **Home → Get data → Blank query**.
   - If you do not see Blank query: **Get data → More → Other → Blank query → Connect**.
2. Power Query Editor opens. On the left, the query is probably named `Query1`.
3. **Home → Advanced Editor**.
4. Select all the text in the box (`Ctrl+A`) and delete it.
5. Open `powerquery\Hierarchy.m` in Notepad or Cursor. Copy the whole file, including `let` and `in`.
6. Paste into Advanced Editor. Click **Done**.
7. In the left **Queries** pane, right-click the query → **Rename**. Type `Hierarchy`. Enter.
8. Look at the preview. You should see 6 rows and columns Region, Country, Sector, Asset ID (Asset A through Asset F).

### 2.2 BS by Region

1. In Power Query, **Home → New Source → Blank Query**.
2. **Home → Advanced Editor**. Select all, delete, paste all of `powerquery\BS by Region.m`. **Done**.
3. Rename the query to `BS by Region` (space, capital R). The name must match the DAX.
4. Preview checks:
   - Column names: Asset ID, Category, Category Sort, Scenario, Amount, Scenario Sort.
   - No row where Category = AUM.
   - Scenario values are only `YTD Actual`, `Annual Forecast`, `Annual Budget`.
   - Bottom-left row count is **72**.

### 2.3 KPI's

1. **Home → New Source → Blank Query**.
2. Advanced Editor. Paste all of `powerquery\KPIs.m`. **Done**.
3. Rename the query to `KPI's` including the apostrophe.
4. Preview checks:
   - Columns: Asset ID, Amount, Metric, TimeView, Scenario, Metric Sort.
   - Metrics, in sort order: NOI, Interest, Net G&A, FF&E Amort, Recoverable Capital Amort, Current Income Tax, Current Capital Tax, MTM Assets, MTM Debt, Other Gain / Loss, Net Income.
   - TimeView is only `YTD` or `Annual`.
   - Scenario is only `Actual`, `Budget`, or `Forecast`. There is no Variance.
   - Only one row per Asset E for a given metric (Asset E was 10 rows in Excel; it is now one asset).
   - Row count is **264**.

### 2.4 Equity Bridge

1. **Home → New Source → Blank Query**.
2. Advanced Editor. Paste all of `powerquery\Equity Bridge.m`. **Done**.
3. Rename the query to `Equity Bridge`.
4. Preview: columns Region, Scenario, Attribution Category, Bridge, Annual Impact, Sort Order, Scenario Sort. Row count **117**. Scenarios are `Jan 2019`, `Jun 2019`, `Dec 2019`.

### 2.5 If Power Query asks about privacy

A yellow bar or a dialog may say the privacy level of the file is not set.

1. Click the message, or **File → Options and settings → Options → Privacy** (this Options menu is inside Power Query, or in Desktop under CURRENT FILE).
2. Easiest fix for this case file only: **File → Options and settings → Options → CURRENT FILE → Privacy → Ignore the Privacy Levels**.
3. Click **OK**, then **Home → Refresh Preview**.

Do not change the Excel path inside the scripts unless you moved `Test Case.xlsx`. The path in each file is:

`C:\Users\khyat\OneDrive\Desktop\OMERS CASE STUDY\Test Case.xlsx`

### 2.6 Load

1. **Home → Close & Apply**.
2. Wait until the refresh finishes. You should land on a blank report page.
3. Left **Data** view (table icon). Click each table and read the row count in the status bar. It must match the table in section 0.

If a query failed, open **Transform data**, click the query with the yellow warning, read the error at that step, and fix only that query’s Advanced Editor. Do not rebuild the steps by clicking the ribbon.

---

## 3. Model view: relationships and sort

1. Click the **Model** view icon on the left (three boxes).
2. If any line already connects two tables, click the line and press **Delete**. You want to draw them yourself.

### 3.1 Draw the two relationships

1. Drag **Hierarchy[Asset ID]** onto **BS by Region[Asset ID]**.
2. In the dialog:
   - Cardinality: **One to many (1:*)**
   - Cross filter direction: **Single**
   - Make this relationship active: checked
   - Assume referential integrity: unchecked
3. Click **OK**.
4. Drag **Hierarchy[Asset ID]** onto **KPI's[Asset ID]**. Same settings. **OK**.

There must be **no line** from Equity Bridge to anything. There must be **no line** between BS by Region and KPI's.

If Power BI offers Many-to-many, stop. The grouping step did not run. Go back to Transform data and confirm row counts.

### 3.2 Sort by column

Click the **Data** view.

For each row below: click the column in the fields list or the grid header so it is selected, then **Column tools → Sort by column** and pick the sort column.

| Select this column | Sort by column |
|---|---|
| BS by Region → Category | Category Sort |
| BS by Region → Scenario | Scenario Sort |
| KPI's → Metric | Metric Sort |
| Equity Bridge → Attribution Category | Sort Order |
| Equity Bridge → Scenario | Scenario Sort |

### 3.3 Hide columns you must not drag onto visuals

In Data view, right-click the column → **Hide in report view**:

On **BS by Region**: Category Sort, Scenario Sort.

On **KPI's**: Metric Sort, TimeView, Scenario.

On **Equity Bridge**: Sort Order, Scenario Sort, Annual Impact.

Leave visible: Hierarchy Region, Country, Sector, Asset ID. BS Category, Scenario, Amount, Asset ID. KPI Metric, Amount, Asset ID. Equity Bridge Region, Scenario, Attribution Category, Bridge.

### 3.4 Country names for the map

Filled map does not recognise `USA` or `UK`. Add one column on Hierarchy. This is not a new table.

1. Data view, click the **Hierarchy** table.
2. **Table tools → New column**.
3. Replace the formula bar with:

```dax
Country Map =
SWITCH (
    Hierarchy[Country],
    "USA", "United States",
    "UK", "United Kingdom",
    Hierarchy[Country]
)
```

4. Press Enter. You should see Canada, United States, United Kingdom, Australia, Singapore.

---

## 4. Measures (one at a time)

You cannot paste `DAX_measures.dax` as a single measure. Each block is its own measure. The name is the text before `=`.

1. Click the **Report** view.
2. In the Data pane, click the **Hierarchy** table so it is selected. Every measure must live on Hierarchy.
3. **Home → New measure** (or right-click Hierarchy → New measure).
4. Paste one measure, including the name. Example, the first one is only:

```dax
Amount =
SUM ( 'BS by Region'[Amount] )
```

5. Press **Enter** or click the check mark.
6. Repeat New measure for every measure in `DAX_measures.dax`, in this order:

1. Amount
2. AUM
3. GAV
4. Equity
5. Equity Forecast
6. Equity OP
7. KPI Amount
8. YTD Actual
9. YTD Budget
10. YTD Var
11. Annual Forecast
12. Annual Budget
13. Annual Var
14. NI YTD Actual
15. NI YTD Budget
16. NI Forecast
17. NI Budget
18. NOI YTD Actual
19. MTM Assets YTD
20. MTM Debt YTD
21. Performance Return Forecast
22. Performance Return Budget
23. Performance Return Var pp
24. Performance Return YTD
25. Bridge Amount
26. Asset Title

If a measure lands on the wrong table: click the measure, **Measure tools → Home table → Hierarchy**.

### 4.1 Format the measures

Click the measure, then **Measure tools → Format**.

| Measure | Format | Decimal places |
|---|---|---|
| Performance Return Forecast | Percentage | 1 |
| Performance Return Budget | Percentage | 1 |
| Performance Return YTD | Percentage | 1 |
| Performance Return Var pp | Percentage | 1 |
| Amount, AUM, GAV, Equity, Equity Forecast, Equity OP | Currency, $ English (United States) | 0 |
| KPI Amount, YTD Actual, YTD Budget, YTD Var, Annual Forecast, Annual Budget, Annual Var | Currency | 0 |
| NI YTD Actual, NI YTD Budget, NI Forecast, NI Budget | Currency | 0 |
| NOI YTD Actual, MTM Assets YTD, MTM Debt YTD | Currency | 0 |
| Bridge Amount | Currency | 0 |
| Asset Title | Text (leave General) |  |

Charts will override display units to millions or billions later. Do not set the measure itself to millions, or the matrix and the cards will both shrink.

### 4.2 Quick number check

1. Report view. Drop a **Card** on the canvas. Field: **Performance Return Forecast**. It should read **6.4%**.
2. Change the field to **Performance Return Budget**. It should read **13.7%**.
3. Change it to **Performance Return Var pp**. It should read **−7.3%** (that is −7.3 percentage points).
4. Delete this test card. You will build the real cards in the next section.

If the card is blank, the relationship or the measure home table is wrong. Stop and fix section 3 before drawing pages.

---

## 5. Page setup (do this on every page)

You will have three pages. Rename them before you build:

1. Bottom of the screen, double-click **Page 1**. Name it `Portfolio performance`.
2. Click the **+** to add a page. Name it `IS details`.
3. Add another page. Name it `Equity movements`.

For **each** of the three pages:

1. Click a blank part of the page (not a visual).
2. **Format** pane (paint roller) → **Page information** is not needed.
3. Expand **Canvas background**.
   - Color: click the paint square → **More colors** → Hex `#F2F2F2`.
   - Transparency: **0%**.
4. Expand **Wallpaper**. Color `#F2F2F2`, Transparency **0%**.
5. **Canvas settings**: leave **16:9** (1280 × 720). **View → Page view → Fit to page** while you build, then **Actual size** when you check alignment.

Every visual you add, set this before you move on (Format visual → **General**):

- **Properties → Size**: you will place them by eye; keep a small gap, about 8 px, between visuals.
- **Effects → Background**: On, color `#FFFFFF`, transparency 0%.
- **Effects → Visual border**: On, color `#E1DFDD`, width 1, rounded corners 0.
- **Effects → Shadow**: Off.
- **Title**: On. Font Segoe UI, 12, bold, color `#605E5C`. Text is given per visual below.
- Turn off **Visual header** only if you want a cleaner screenshot. Leave it on while building so you can see the filter icon.

---

## 6. Page 1 — Portfolio performance

Build top to bottom: slicers, map, cards, gauge, matrix, two stacked charts, two extra charts.

### 6.1 Three slicers

**Region**

1. Visualizations pane → **Slicer** (funnel icon).
2. Drag **Hierarchy → Region** into Field.
3. Format visual → **Slicer settings → Options**: Style = **Tile**. Single select = **Off**. Select all is optional; leave it off. With nothing selected, the page shows all regions.
4. **Slicer settings → Selection**: Show “Select all” = Off.
5. Format → **Values**: Font Segoe UI 11.
6. To color the selected tile: Format → **Slicer settings** → Values → you may only get font color. If your version has **Selection icons / Buttons**: Selected fill `#0B3A5B`, selected font white. If you cannot set tile fill, leave the default blue and do not fight it.
7. Title: `Region`.

**Country** — same steps. Field = **Hierarchy[Country]**. Title `Country`.

**Sector** — same steps. Field = **Hierarchy[Sector]**. Title `Sector`.

Place them in one row under the top of the page. Do not put Asset ID in a slicer.

### 6.2 Country map

1. Visualizations → **Filled map** (globe with solid countries). If you only have **Map** (bubbles), use that instead. Prefer Filled map.
2. Location = **Hierarchy[Country Map]** (the column you added, not Country).
3. Tooltip: drag **Hierarchy[Country]** and the measure **AUM**.
4. This map would add YTD + Forecast + Budget together if you do not filter it. Open the **Filters** pane. Under **Filters on this visual** (not on this page), drag **BS by Region[Scenario]**. Basic filtering. Check only **YTD Actual**.
5. Title: `AUM by country`.
6. Format → **Map settings**: if there is Auto zoom, turn it on. **Bubbles** or fill color: default blue is fine; if you can set a single color, use `#0B3A5B`.
7. Click Canada on the map once. The cards and charts should shrink to Canadian assets (A and B). Click Canada again to clear. If nothing filters, Location is not on Hierarchy. Fix that before continuing.

The Toronto photo is optional decoration. It is not the country map the brief asked for. If you still want it, **Insert → Image** and place `toronto_slicer.jpg` at the right of the slicer row. Do not use it as the Location field.

### 6.3 Three cards

Card 1

1. Visualizations → **Card**.
2. Field: **Performance Return Forecast**.
3. Title: `Performance Return · Forecast`.
4. Format → **Callout value**: color `#252423`, display units None (the % format on the measure is enough).
5. Turn **Category label** Off so you do not see the measure name twice.

Card 2: field **Performance Return Budget**. Title `Performance Return · Budget`.

Card 3: field **Performance Return Var pp**. Title `Variance`. Callout color: you cannot easily make one card red only when negative without a conditional format. Format → Callout value → color `#A4262C` for this card only, because at the total-portfolio level the variance is negative. If a slicer later makes it positive, change is not automatic. That is acceptable.

With no slicer selected, the three cards read **6.4%**, **13.7%**, **−7.3%**.

### 6.4 Gauge

1. Visualizations → **Gauge**.
2. **Value** = Performance Return Forecast.
3. **Target value** = Performance Return Budget.
4. Do not put anything in Minimum, Maximum, or Tooltips yet.
5. Format → **Gauge axis**: Min **0**, Max **0.2** (that is 20%, so 13.7% fits).
6. Format → **Colors**: Fill `#0B3A5B`. Target `#A4262C` if the target sits above the value, or leave target as a dark tick.
7. Format → **Data labels**: On, percentage.
8. Format → **Callout value**: On.
9. Title: `Return gauge`.
10. The needle should sit near 6.4% and the target tick near 13.7%.

### 6.5 Income statement matrix

1. Visualizations → **Matrix** (not Table).
2. **Rows** = KPI's[Metric].
3. **Columns**: leave empty.
4. **Values**, in this order (drag to reorder inside the well):
   1. YTD Actual
   2. YTD Budget
   3. YTD Var
   4. Annual Forecast
   5. Annual Budget
   6. Annual Var
5. Do not add TimeView, Scenario, or Asset ID.
6. You should see 11 rows, NOI at the top, Net Income at the bottom. Net Income YTD Actual is about **$73.7 million** if you set display units to millions, or **$73,691,492** if units are none.
7. Title: `Income statement`.

Display units (do this so the matrix matches the preview):

1. Format visual → **Specific column** or **Cell elements** / **Values**.
2. Display units = **Millions**. Value decimal places = **1**.
3. Apply to all six value columns if the pane makes you pick one series at a time.

Grid:

1. Format → **Grid** → Horizontal grid On, color `#E1DFDD`. Vertical grid Off.
2. Format → **Column headers**: Segoe UI, `#605E5C`, bold.
3. Format → **Row headers**: Segoe UI, `#252423`.
4. Format → **Style presets**: None or Minimal. Not Alternating rows in a loud color.

Variance icons (do this twice, once for YTD Var and once for Annual Var):

1. In the Visualizations well, click the small arrow next to **YTD Var** → **Conditional formatting → Icons**.
2. Format style: **Rules**.
3. Base field: the same measure, YTD Var. Summarization: Sum.
4. Rule 1: if value **is greater than** **0** → Icon: up arrow, color `#107C10`.
5. **+ New rule**: if value **is less than** **0** → Icon: down arrow, color `#A4262C`.
6. Icon layout: **Right of data** (or Left, just be consistent).
7. Click **OK**.
8. Repeat for **Annual Var**.

Net Income YTD Var should be a red down arrow (actual is far below budget because of Other Gain / Loss). NOI YTD Var should be a green up arrow.

### 6.6 Stacked column — AUM (instruction 8)

1. Visualizations → **Stacked column chart**. Not Clustered. Not 100% stacked.
2. **X-axis** = BS by Region[Scenario].
3. **Y-axis** = Amount. Not AUM. Amount, with the filter below, is the stack. If you use the AUM measure and also put Category in the legend, each segment is filtered twice and can look empty.
4. **Legend** = BS by Region[Category].
5. **Filters on this visual** → drag Category → check only **Equity**, **Debt**, **3rd Party**. Leave Real Estate unchecked. This filter must say “On this visual”, not “On this page”.
6. The X-axis order must be YTD Actual, Annual Forecast, Annual Budget. That comes from Scenario Sort. If the order is alphabetical, section 3.2 was skipped.
7. Legend position: Format → **Legend** → Position **Bottom**. Legend text Segoe UI 10.
8. Format → **Columns → Colors**. Set them by series name, not by “apply to all”:
   - Equity `#0B3A5B`
   - Debt `#00B7C3`
   - 3rd Party `#CA8A04`
9. Y-axis: Title `AUM ($ billions)`. Display units **Billions**. Decimal places **2**. Color `#605E5C`.
10. X-axis title: `Scenario`.
11. Data labels: **Off**.
12. Title: `AUM = Equity + Debt + 3rd Party`.
13. You should see three columns. YTD is the tallest, about **$7.86B**. Forecast about **$6.18B**. Budget about **$6.15B**.

### 6.7 100% stacked column — sector (instruction 9)

1. Visualizations → **100% stacked column chart**.
2. **X-axis** = BS by Region[Scenario].
3. **Y-axis** = **GAV** (the measure, not Amount).
4. **Legend** = Hierarchy[Sector].
5. No Category filter on this visual. GAV already keeps Real Estate only.
6. Legend position **Bottom**.
7. Format → Columns → Colors:
   - Industrial `#0B3A5B`
   - Office `#118DFF`
   - Retail `#038387`
   - Hotel `#CA5010`
   - Residential `#8764B8`
8. Y-axis title: `Share of real estate value`. It should run 0% to 100%.
9. X-axis title: `Scenario`.
10. Data labels Off.
11. Title: `Real estate value mix by sector`.
12. Industrial is the large navy block on every column (about 63% of YTD). Office and Retail are the next bands. Hotel and Residential are thin.

### 6.8 Return by asset (instruction 11)

1. Visualizations → **Clustered bar chart** (horizontal bars).
2. **Y-axis** = Hierarchy[Asset ID].
3. **X-axis** = Performance Return Forecast.
4. Click the **...** on the visual → **Sort axis → Performance Return Forecast**. Then sort **descending** so Asset F is on top (about **15.3%**). Asset C is about **4.1%**.
5. Format → Bars → Color `#0B3A5B` (one series, so one color).
6. Data labels **On**. Display units None (percentage).
7. X-axis title: `Forecast return`. Y-axis title: `Asset`.
8. Legend: **Off** (only one series).
9. Title: `Performance return by asset · Forecast`.
10. This visual is what you right-click later to drill through. Asset ID must stay on the axis.

### 6.9 NOI vs mark-to-market (instruction 11)

1. Visualizations → **Stacked bar chart**.
2. **Y-axis** = Hierarchy[Asset ID].
3. **X-axis**, three measures: NOI YTD Actual, MTM Assets YTD, MTM Debt YTD.
4. Legend **Bottom**.
5. Colors: NOI `#038387`, MTM Assets `#CA8A04`, MTM Debt `#A4262C`.
6. X-axis display units **Millions**, 1 decimal. Title `YTD $ millions`.
7. Data labels Off.
8. Title: `NOI vs MTM (YTD)`.
9. MTM Debt is negative, so its bar grows to the left of zero. That is correct. Asset F is almost only gold (mark-to-market real estate, no NOI).

### 6.10 Drillthrough setup from this page

You do not add a drillthrough well on page 1. You only need Asset ID on the bar chart. The destination is configured on page 2. Finish page 2, then come back and test: right-click **Asset B** on the return bar → **Drill through → IS details**.

---

## 7. Page 2 — IS details

Click the **IS details** page tab.

1. Set the grey canvas again (section 5) if this page is still white.
2. Click a blank area of the page.
3. **Visualizations** pane, drag **Hierarchy[Asset ID]** into the **Drill through** well (it sits under the Build tab, below Values; it is labelled “Add drill-through fields here”).
4. A back-arrow button appears at the top left. Leave it.
5. In the Drill through well, click Asset ID. **Keep all filters** = **On**.
6. Cross-report drillthrough = Off.

Title row. Use three **Card** visuals, not a chart:

| Card field | Title |
|---|---|
| Asset Title | Asset |
| Hierarchy[Country] — use a card; if it asks for a measure, use **Table tools** is wrong. For a text column on a card, Power BI uses First. Drag Country onto a Card. | Country |
| Hierarchy[Sector] the same way | Sector |

If a card refuses a text column, use a **Multi-row card** instead and put Asset Title, Country, and Sector on that one visual. Title of that visual: `Selected asset`.

Then copy the income statement:

1. Go back to **Portfolio performance**.
2. Click the matrix. **Ctrl+C**.
3. Open **IS details**. **Ctrl+V**.
4. Confirm rows are still Metric and the six measures are unchanged.
5. Title: `Income statement details · all KPIs`.
6. Do not add any other chart on this page.

Test:

1. On page 1, right-click Asset B on the return-by-asset bar → Drill through → IS details.
2. The page should say Asset B, Canada, Retail.
3. NOI YTD Actual about **22.1 million**. Net Income Forecast about **28.3 million**.
4. Click the back arrow. You should return to page 1.

---

## 8. Page 3 — Equity movements

Only a waterfall and two slicers. No country slicer. No sector slicer. No second chart.

1. Grey canvas, section 5.
2. Slicer. Field = **Hierarchy[Region]**. Style = Tile. Single select = Off. Title `Region`.
3. Slicer. Field = **Equity Bridge[Scenario]**. Style = Tile. **Single select = On**. Click **Dec 2019** so it is the saved selection. Title `Scenario`.
4. These two slicers must **not** be the same objects as page 1. Build them new on this page.

Waterfall:

1. Visualizations → **Waterfall chart**.
2. **Category** = Equity Bridge[Attribution Category].
3. **Y-axis** = Bridge Amount.
4. Leave **Breakdown** empty.
5. The category order must start with **Opening** and end with **Miscellaneous**. That is Sort Order. If it is alphabetical, go back to section 3.2.
6. Format → **Sentiment colors** (the increase / decrease / total colors):
   - Increase `#107C10`
   - Decrease `#A4262C`
   - Total `#0B3A5B`
7. Y-axis display units **Billions**, 2 decimals. Title `Equity ($ billions)`.
8. X-axis title off if the category names already show. Turn **Data labels** On.
9. Legend Off.
10. Title: `Equity bridge · Jan 1 to Dec 31, 2019`.
11. With Scenario = Dec 2019 and Region = all, Opening is **13.00** billion and the total column is about **15.54** billion. The big green bars are Capex/Leasing (**+1.69**) and Acquisitions (**+1.35**). The big red bar is Dispositions (**−1.01**).

Click only **North America** on the Region slicer. The opening should drop from 13 to **10**. Click it again to clear.

Do not add a column chart of the three dates. The Scenario slicer is how you move between Jan, Jun, and Dec.

---

## 9. Sync slicers (page 1 and page 2 only)

1. **View → Sync slicers**. A pane opens on the right.
2. Click the **Region** slicer on page 1.
3. In the sync pane, check the sync box for **Portfolio performance** and **IS details** only. Leave **Equity movements** unchecked.
4. Do the same for the page 1 **Country** slicer and the page 1 **Sector** slicer.
5. Click the page 3 Region slicer and the page 3 Scenario slicer. Their sync boxes should be checked only on **Equity movements**.
6. Close the sync pane.

Why: page 3 is region grain. If the Canada slicer from page 1 also filtered page 3, the waterfall would still show all of North America, which looks like a bug.

---

## 10. Save and the final click-through

1. **File → Save as**.
2. Folder: `C:\Users\khyat\OneDrive\Desktop\OMERS CASE STUDY`.
3. Name: `OMERS Case Study.pbix`.

Then do this once, with no slicers selected on page 1:

1. Cards: 6.4%, 13.7%, −7.3 pp.
2. Matrix Net Income row: YTD Actual 73.7, YTD Budget 217.3, red variance; Annual Forecast 130.6, Annual Budget 275.2, red variance. Units in millions.
3. AUM stacks: three columns, legend Equity / Debt / 3rd Party, YTD tallest.
4. Sector chart: three columns, each totaling 100%, Industrial the largest slice.
5. Right-click Asset B → IS details → NOI about 22.1 million → back arrow.
6. Equity movements, Dec 2019: opening 13.00, total about 15.54. Switch the slicer to Jan 2019: almost only Opening (the other categories are zero). Switch back to Dec 2019 before you close the file so that is the saved state.

---

## 11. If something breaks

| What you see | What to do |
|---|---|
| Many-to-many between BS and KPI's | Delete that relationship. Do not turn on Both cross-filter. |
| Many-to-many on Region | You dragged Equity Bridge[Region] to Hierarchy. Delete it. The waterfall uses the Bridge Amount measure. |
| Matrix numbers are huge, like 10× too big | A relationship between the two facts exists, or you put Scenario on the matrix columns as well as the measures. Remove it. |
| AUM chart has four legend items including Real Estate | The visual-level Category filter is missing or was set on the page. |
| AUM chart is three separate clusters, not stacks | You picked Clustered column chart. Change the visual type to Stacked column chart. |
| Sector chart is not 100% | You picked Stacked column chart. Change it to 100% stacked column chart, Y-axis = GAV. |
| Map is blank | Location must be Country Map, not Country. USA and UK are renamed in that column. |
| Gauge is a full circle at 640% | Max is 1 or 100. Set Min 0 and Max 0.2. |
| Waterfall order is alphabetical | Attribution Category is not sorted by Sort Order. |
| Waterfall is blank | Bridge Amount was not used, or you related the tables and the filter wiped the bridge. Use the measure. Delete any Equity Bridge relationship. |
| Asset E appears 10 times | KPI's or BS grouping did not run. Re-paste that query. |
| Advanced Editor error on KPI's about Description | The sheet name is not `KPI's`, or the file path is wrong. |
| Privacy / Formula.Firewall error | Section 2.5. Ignore privacy levels for this file, then refresh. |
