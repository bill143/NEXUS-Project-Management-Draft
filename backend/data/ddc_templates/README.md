# DDC Reference Templates

Excel templates copied verbatim from DataDrivenConstruction reference repos. They serve as canonical formats that NEXUS modules read or generate.

| File | Source repo | Used by | Purpose |
|---|---|---|---|
| `open_estimation/OpenEstimator.xlsx` | `Open-Estimation` | `boq` + `costs` | Reference shape for full BOQ workbooks (sections, positions, cost tables) |
| `open_estimation/Grouping_rules_QTO.xlsx` | `Open-Estimation` | `ddc_qto` | Per-category grouping/aggregation rule lists — feeds `ddc_qto.group_and_aggregate` |

## Adding more templates

When porting a new DDC reference repo that ships an `.xlsx` template, drop it under a subdirectory named after the source repo (snake_case) and add a row above. Keep individual files under 5 MB; large datasets belong in `data/cwicr/` or external storage.
