// Paste into the "Equity Bridge" query (Advanced Editor).
// Region grain. Do not relate this table to Hierarchy.
let
    FilePath = "C:\Users\khyat\OneDrive\Desktop\OMERS CASE STUDY\Test Case.xlsx",
    Source = Excel.Workbook(File.Contents(FilePath), false, true),
    Sheet = Source{[Item = "Equity Bridge", Kind = "Sheet"]}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            {"Region", type text},
            {"Scenario", type text},
            {"Attribution Category", type text},
            {"Bridge", type number},
            {"Annual Impact", type number},
            {"Sort Order", Int64.Type},
            {"Scenario Sort", Int64.Type}
        }
    ),
    Kept = Table.SelectRows(
        Typed,
        each [Region] <> null and [#"Attribution Category"] <> null
    )
in
    Kept
