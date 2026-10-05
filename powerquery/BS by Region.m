// Paste into the "BS by Region" query (Advanced Editor).
// Drops AUM (it is Equity + Debt + 3rd Party in DAX), collapses Asset E/F,
// then unpivots the three scenarios so the stacked charts can compare them.
let
    FilePath = "C:\Users\khyat\OneDrive\Desktop\OMERS CASE STUDY\Test Case.xlsx",
    Source = Excel.Workbook(File.Contents(FilePath), false, true),
    Sheet = Source{[Item = "BS by Region", Kind = "Sheet"]}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"Category", type text},
            {"Asset ID", type text},
            {"YTD Actual", type number},
            {"Forecast", type number},
            {"Operating Plan", type number},
            {"Category Sort", Int64.Type}
        }
    ),
    NoAum = Table.SelectRows(Typed, each [Category] <> null and [Category] <> "AUM"),
    Rounded = Table.TransformColumns(
        NoAum,
        {
            {"YTD Actual", each Number.Round(_, 2), type number},
            {"Forecast", each Number.Round(_, 2), type number},
            {"Operating Plan", each Number.Round(_, 2), type number}
        }
    ),
    Grouped = Table.Group(
        Rounded,
        {"Asset ID", "Category", "Category Sort"},
        {
            {"YTD Actual", each List.Sum([YTD Actual]), type number},
            {"Forecast", each List.Sum([Forecast]), type number},
            {"Operating Plan", each List.Sum([Operating Plan]), type number}
        }
    ),
    Unpivoted = Table.Unpivot(
        Grouped,
        {"YTD Actual", "Forecast", "Operating Plan"},
        "Scenario",
        "Amount"
    ),
    RenamedForecast = Table.ReplaceValue(
        Unpivoted,
        "Forecast",
        "Annual Forecast",
        Replacer.ReplaceText,
        {"Scenario"}
    ),
    RenamedBudget = Table.ReplaceValue(
        RenamedForecast,
        "Operating Plan",
        "Annual Budget",
        Replacer.ReplaceText,
        {"Scenario"}
    ),
    WithSort = Table.AddColumn(
        RenamedBudget,
        "Scenario Sort",
        each
            if [Scenario] = "YTD Actual" then 1
            else if [Scenario] = "Annual Forecast" then 2
            else 3,
        Int64.Type
    )
in
    WithSort
