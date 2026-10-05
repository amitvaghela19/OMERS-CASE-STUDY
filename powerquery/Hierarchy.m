// Paste into the Hierarchy query (Advanced Editor).
// Do not load Instructions, Returns, or Sheet1.
let
    FilePath = "C:\Users\khyat\OneDrive\Desktop\OMERS CASE STUDY\Test Case.xlsx",
    Source = Excel.Workbook(File.Contents(FilePath), false, true),
    Sheet = Source{[Item = "Hierarchy", Kind = "Sheet"]}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
    Trimmed = Table.TransformColumns(
        Promoted,
        {
            {"Region", each Text.Trim(Text.From(_)), type text},
            {"Country", each Text.Trim(Text.From(_)), type text},
            {"Sector", each Text.Trim(Text.From(_)), type text},
            {"Asset ID", each Text.Trim(Text.From(_)), type text}
        }
    ),
    Kept = Table.SelectRows(Trimmed, each [#"Asset ID"] <> null and [#"Asset ID"] <> "")
in
    Kept
