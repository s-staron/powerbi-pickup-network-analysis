# 07 Release notes

## v1.0.1 (17 November 2026)

Fixes two problems found after v1.0.0: the project did not load in Power BI Desktop because of a misplaced description in the row-level security role (the TMDL folder now loads with Desktop's own serializer), and the keyboard tab order ran from the last visual to the first. Details: doc 06, defects D7 and D8. Power Query, DAX and the report pages (PBIR) still need their first full check in Desktop.

## v1.0.0 (17 November 2026)

First release of the pickup network report for Norvane Parcel (a fictional carrier; all data is synthetic).

### What is in the release

**Data**

- Seeded generator for 133,601 parcels (134,838 export rows) at 90 pickup points in 5 regions, July 2024 to December 2025, plus monthly targets per region.
- Six planted data quality issues (R1 to R6) that Power Query handles and the documentation records.

**Semantic model** (`PickupNetwork.SemanticModel`, TMDL)

- Star schema with `FactParcel`, `DimPickupPoint`, `DimDate`, `DimRegion` and `Target`; five many-to-one, single-direction relationships; hidden keys.
- `DataFolder` parameter, staging queries, reusable M functions and one named step per quality rule.
- Date table built in Power Query and marked as the date table.
- 30 DAX measures with descriptions, format strings and display folders: counts, DIVIDE-based rates, dwell time, utilisation, MTD, YTD, previous year, YoY, rolling 3 months, targets and variance, `ALL` and `ALLSELECTED` shares, Top N and Bottom N, dynamic titles, conditional colour and reconciliation.
- Field parameter `Headline KPI` and parameter table `Top N`.
- Row-level security role `Regional Manager` (dynamic, with a user-region mapping table).

**Report** (`PickupNetwork.Report`, PBIR)

- Executive overview, Network performance, Point detail (drill-through) and Data quality and reconciliation, plus a hidden tooltip page.
- One theme file with a colour-blind-safe palette, alt text and tab order on all 37 visuals.

**Validation**

- `validation/reconcile.py` recomputes every KPI from the raw files and writes `expected_results.csv` (149 values).
- `validation/sql_crosscheck.py` repeats the base KPIs in SQL: 86 values, no differences.
- `validation/validate_project.py` validates files against Microsoft's JSON schemas and checks the model and report structure: 582 checks, none failed.

**Documentation**: README, documents 01 to 07 and this changelog.

### Not verified in this release

The project was built in an environment without the Power BI Modeling MCP, and Power BI Desktop could not be driven from a script (opening the `.pbip` from the command line gave an empty report). Therefore:

- Power Query and DAX have not been run. The report's reconciliation page does that comparison the first time the file is refreshed in Desktop.
- Row-level security, drill-through, tooltips, slicer sync and conditional formatting have not been tried in Desktop.
- Accessibility checker and refresh time have not been measured.

See doc 06, section 6, for the first things to check.

### Known limitations

- Targets exist per region and month only. Target measures are blank for single points.
- Utilisation is an average over the selected period. Peak days are not shown.
- Previous-year comparisons start in July 2025 because the data starts in July 2024.
- Parcels at unmatched point IDs (457 of 133,601) are shown as Unassigned.
- The `DataFolder` default is a placeholder path; set it before the first refresh.
- No phone layout; no scheduled refresh (CSV source).

### How to open

1. Install Power BI Desktop for Windows (a current monthly release).
2. Clone the repository and open `PickupNetwork.pbip`.
3. Home, Transform data, Edit parameters: set `DataFolder` to the repository folder.
4. Refresh and open page 4: all reconciliation rows should show OK.

### Assumptions to confirm (see doc 01, sections 9 and 10)

Storage period of 7 days, the 82% pickup-speed target, utilisation thresholds of 85% and 15%, capacity measured in parcel slots.
