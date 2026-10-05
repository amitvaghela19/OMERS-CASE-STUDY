// Paste into the "KPI's" query (Advanced Editor).
// Excel still has 16 junk rows above the real header. This skips them,
// sums Asset E to one asset, drops stored variances, and unpivots to
// Metric / TimeView / Scenario so the income statement can sit on rows.
let
    FilePath = "C:\Users\khyat\OneDrive\Desktop\OMERS CASE STUDY\Test Case.xlsx",
    Source = Excel.Workbook(File.Contents(FilePath), false, true),
    Sheet = Source{[Item = "KPI's", Kind = "Sheet"]}[Data],
    Skipped = Table.Skip(Sheet, 16),
    Promoted = Table.PromoteHeaders(Skipped, [PromoteAllScalars = true]),
    DroppedDescription = Table.RemoveColumns(Promoted, {"Description"}),
    ValueColumns = List.RemoveItems(Table.ColumnNames(DroppedDescription), {"Asset ID"}),
    Typed = Table.TransformColumnTypes(
        DroppedDescription,
        List.Transform(ValueColumns, each {_, type number})
    ),
    Grouped = Table.Group(
        Typed,
        {"Asset ID"},
        List.Transform(
            ValueColumns,
            (col) => {col, (tbl) => List.Sum(Table.Column(tbl, col)), type number}
        )
    ),
    Unpivoted = Table.UnpivotOtherColumns(Grouped, {"Asset ID"}, "Attribute", "Amount"),
    Parse = (attr as text) as record =>
        let
            Rules = {
                {"-YTD Variance", "YTD", "Variance"},
                {"-YTD Budget", "YTD", "Budget"},
                {"-Forecast", "Annual", "Forecast"},
                {"-Budget", "Annual", "Budget"},
                {"-Variance", "Annual", "Variance"},
                {"-Actual", "YTD", "Actual"}
            },
            Hit = List.First(List.Select(Rules, each Text.EndsWith(attr, _{0})), {"", "", ""}),
            Metric = Text.Start(attr, Text.Length(attr) - Text.Length(Hit{0}))
        in
            [Metric = Metric, TimeView = Hit{1}, Scenario = Hit{2}],
    WithParsed = Table.AddColumn(Unpivoted, "Parsed", each Parse([Attribute])),
    Expanded = Table.ExpandRecordColumn(
        WithParsed,
        "Parsed",
        {"Metric", "TimeView", "Scenario"}
    ),
    NoVariance = Table.SelectRows(Expanded, each [Scenario] <> "Variance" and [Scenario] <> ""),
    MetricSorts = [
        NOI = 1,
        Interest = 2,
        #"Net G&A" = 3,
        #"FF&E Amort" = 4,
        #"Recoverable Capital Amort" = 5,
        #"Current Income Tax" = 6,
        #"Current Capital Tax" = 7,
        #"MTM Assets" = 8,
        #"MTM Debt" = 9,
        #"Other Gain / Loss" = 10,
        #"Net Income" = 11
    ],
    WithMetricSort = Table.AddColumn(
        NoVariance,
        "Metric Sort",
        each Record.Field(MetricSorts, [Metric]),
        Int64.Type
    ),
    RemovedAttribute = Table.RemoveColumns(WithMetricSort, {"Attribute"})
in
    RemovedAttribute
