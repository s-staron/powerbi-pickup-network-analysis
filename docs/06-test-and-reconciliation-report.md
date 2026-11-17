# 06 Test and reconciliation report

Version 1.0. Every row says how the check was run. A check that was not run is marked **Not run**; none is presented as passed.

## 1. Summary

| Area | Result |
|------|--------|
| Data generation is reproducible | Passed (run) |
| Planted data quality issues are found by the cleaning rules | Passed (run) |
| Expected KPI values recomputed a second time in SQL | Passed: 86 values compared, 0 differences (run) |
| Project files valid against Microsoft's JSON schemas | Passed: 50 JSON files (run) |
| TMDL and PBIR structure and references | Passed: 577 static checks, 0 failed (run) |
| Power Query refresh in Power BI Desktop | **Not run** |
| DAX measures evaluated and compared with `expected_results.csv` | **Not run** |
| Row-level security tested in Desktop | **Not run** |
| Visual rendering, drill-through, tooltip, slicer sync | **Not run** |
| Accessibility checker, performance, refresh time | **Not run** |

Why the last five rows were not run: the Power BI Modeling MCP was not available in the environment in which the project was built. Power BI Desktop is installed on that machine, but it could not be driven from a script: starting it with the `.pbip` path as an argument opened an empty untitled report instead of the project, and no tool for clicking through the Desktop interface was available. So nothing could open the project or run a DAX query. The model and report files were validated statically instead. What a user must check after opening the file is in section 6 and in the explainer's "open and check" list. The report's own reconciliation page (149 rows) performs the DAX comparison as soon as the file is refreshed in Desktop.

## 2. How the checks were run

| Tool | Command | What it does |
|------|---------|--------------|
| Generator | `python scripts/generate_data.py` | Writes the raw CSV files; prints the planted issue counts |
| Reconcile | `python validation/reconcile.py` | Applies rules R1 to R6 in Python and writes `validation/expected_results.csv` |
| SQL cross-check | `python validation/sql_crosscheck.py` | Loads the CSV files into SQLite, applies the rules in SQL, recomputes base KPIs and compares them with the expected file |
| Static validation | `python validation/validate_project.py` | JSON schema validation, TMDL lint, PBIR field references |

## 3. Test cases

| ID | Test | Expected | Actual | How run | Status |
|----|------|----------|--------|---------|--------|
| T01 | Regenerate the data with seed 42 into an empty folder; compare SHA-256 of all five CSV files with the committed files | Identical | Identical | Generator, `sha256sum` | Passed |
| T02 | Raw size | 80,000 to 150,000 parcels, 60 to 120 points, 4 to 6 regions, 12 to 18 months, CSV total at most 40 MB | 133,601 parcels (134,838 rows), 90 points, 5 regions, 18 months, about 13 MB | Generator output, `du` | Passed |
| T03 | Duplicate rows: generator plants 1,237, reconcile finds the same | 1,237 | 1,237 | Generator vs reconcile | Passed |
| T04 | Rows with dd.MM.yyyy timestamps | 5,428 | 5,428 | Generator vs reconcile | Passed |
| T05 | Returned parcels without a pickup time (written as `NULL` or as empty text) | 6,700 | 6,700 | Generator vs reconcile | Passed |
| T06 | Parcels at point IDs missing from the points table | 457 rows, 2 IDs | 457 rows, 2 IDs (PP-091: 227, PP-092: 230) | Reconcile | Passed |
| T07 | City spelling variants standardised | 47 points | 47 points; every spelling is in `city_mapping.csv` (no `KeyError`) | Generator vs reconcile | Passed |
| T08 | Opening dates in the dd.MM.yyyy format | 18 | 18 | Generator vs reconcile | Passed |
| T09 | Network KPIs, 7 regions and two months recomputed in SQL (counts, rates, average dwell time, utilisation, data-quality counts) | Equal to the Python results | 86 of 86 equal (tolerance 0.000001 relative) | SQL cross-check | Passed |
| T10 | JSON files valid against their `$schema` | No errors | 50 files, 0 errors | `validate_project.py` | Passed |
| T11 | TMDL: tabs only, unique lineage tags, every table and measure has a description, display folder and (numeric) format string | All true | All true | `validate_project.py` | Passed |
| T12 | Model structure: 5 many-to-one single-direction relationships, key columns hidden, date table marked, auto date/time off, implicit measures discouraged | All true | All true | `validate_project.py` | Passed |
| T13 | 30 measures (limit 20 to 30); every DAX reference resolves to an existing column or measure | True | 30 measures; all references resolve | `validate_project.py` | Passed |
| T14 | RLS role `Regional Manager` exists and filters `DimRegion` by `USERPRINCIPALNAME()` | True | True (text check only) | `validate_project.py` | Passed (static) |
| T15 | Every KPI in `expected_results.csv` is covered by the `Check Actual` measure | All 20 | All 20 | `validate_project.py` | Passed |
| T16 | Every visual field exists in the model; 37 visuals have alt text and tab order; 4 visible pages; tooltip and drill-through bindings consistent | True | True | `validate_project.py` | Passed |
| T17 | Power Query: refresh without errors; fact table 133,601 rows | No errors | | Power BI Desktop | **Not run** |
| T18 | DAX: all 149 reconciliation rows show OK | 149 of 149 | | Power BI Desktop, page 4 | **Not run** |
| T19 | RLS: `north.manager@example.com` sees only North (19,976 parcels) | North only | | Desktop, View as | **Not run** |
| T20 | RLS: an address not in the mapping table sees no data | No data | | Desktop, View as | **Not run** |
| T21 | Drill-through from the matrix opens Point detail filtered to the point | Works | | Desktop | **Not run** |
| T22 | Tooltip page appears on the matrix and on the Top N and Bottom N charts | Works | | Desktop | **Not run** |
| T23 | Slicers Region and Month stay in sync between pages 1 and 2 | Works | | Desktop | **Not run** |
| T24 | Headline KPI slicer switches the line chart | Works | | Desktop | **Not run** |
| T25 | Conditional formatting colours utilisation of 85% or more and under 15% | Works | | Desktop | **Not run** |
| T26 | Accessibility checker, keyboard navigation, screen reader | No issues | | Desktop | **Not run** |
| T27 | Refresh time for 134,838 rows | Under one minute (NF2) | | Desktop | **Not run** |

## 4. Reconciliation of KPI values

The expected values come from `validation/expected_results.csv`. Two independent implementations (Python and SQL) agree on the 86 base values they both cover. The DAX values have not been calculated yet (T18).

| KPI | Expected (network, whole window) | Python | SQL | DAX in the model |
|-----|---------------------------------:|:------:|:---:|:----------------:|
| Parcels arrived | 133,601 | yes | yes | Not run |
| Parcels collected | 126,901 | yes | yes | Not run |
| Parcels returned | 6,700 | yes | yes | Not run |
| Collected within 3 days | 107,131 | yes | yes | Not run |
| Pickup rate | 95.0% | yes | yes | Not run |
| Pickup within 3 days rate | 80.2% | yes | yes | Not run |
| Return to sender rate | 5.0% | yes | yes | Not run |
| Avg dwell days | 1.76 | yes | yes | Not run |
| Utilisation | 29.4% | yes | yes | Not run |
| Overloaded points | 10 | yes | no | Not run |
| Target parcels | 138,670 | yes | no | Not run |
| Parcels vs target % | -3.7% | yes | no | Not run |
| Pickup 3D vs target pp | -1.8 pp | yes | no | Not run |
| Parcels MTD, YTD, PY, YoY, rolling 3M (December 2025) | 12,047; 89,451; 10,141; +18.8%; 29,388 | yes | no | Not run |

Cross-checks inside the expected file: the five regions plus Unassigned add up to 133,601 parcels; the five regional targets add up to 138,670; returned (6,700) plus collected (126,901) equals 133,601.

## 5. Defects found and fixed during the build

| ID | Defect | Found by | Fix |
|----|--------|----------|-----|
| D1 | Some points had utilisation above 300% because random capacities were too small | Profiling the generated data | Capacities raised; overloaded points get a floor capacity; volume multiplier lowered. A few points above 100% remain on purpose |
| D2 | The tooltip page filter used an invalid `howCreated` value | JSON schema validation | Changed to `User` |
| D3 | The theme import version was a string, the schema needs an object | JSON schema validation | Version object with report, page and visual versions |
| D4 | `DimRegion[Region]` was both the name shown to users and the relationship key (a visible key) | Static check "key columns are hidden" | Added a hidden surrogate key `RegionKey`; relationships use it |
| D5 | Target measures would have shown a region's target next to a single point | Design review of the matrix | Target measures return blank when `DimPickupPoint` is filtered |
| D6 | Utilisation would have counted parcels at the unknown point in the numerator but not the denominator | Design review while writing `reconcile.py` | Unknown point is excluded from occupied slot-days |

## 6. Known risks and what to check first in Power BI Desktop

The TMDL and PBIR files were written outside Power BI Desktop. They match the published schemas, but a schema cannot catch everything Desktop checks at load time.

1. Open `PickupNetwork.pbip`. If Desktop reports an error in a file, read the message and the file path; the files are text and easy to fix.
2. Set `DataFolder` and refresh. If a Power Query step fails, the step name says which rule (R1 to R6) it belongs to.
3. Check page 4: 149 rows with status OK. A CHECK row names the KPI, scope and value that differ.
4. The line chart on page 1 uses a field parameter written by hand. If it shows an error, remove the field and add `Headline KPI Fields` again.
5. Run T19 to T26 from the table above and update this document.

## 7. UAT checklist for the stakeholder

Tick each item when it holds.

| # | Check | Page | Expected | OK |
|---|-------|------|----------|----|
| 1 | The report opens on the Executive overview | 1 | Four KPI cards, three slicers, four charts | [ ] |
| 2 | Parcels arrived, no filter | 1 | 133,601, 3.7% below target | [ ] |
| 3 | Pickup within 3 days, no filter | 1 | 80.2%, target 82.0%, -1.8 pp | [ ] |
| 4 | Return to sender, no filter | 1 | 5.0%, target 5.7% | [ ] |
| 5 | Region West selected | 1 | Pickup within 3 days 69.7%, return rate 6.3% | [ ] |
| 6 | Month 2025-12 selected | 1 | 12,047 parcels, +18.8% versus last year | [ ] |
| 7 | Headline KPI slicer set to Utilisation | 1 | Line chart shows utilisation by month | [ ] |
| 8 | Return reasons chart | 1 | Reasons sorted from the largest | [ ] |
| 9 | Matrix: expand a region | 2 | Points appear; utilisation of 85% or more is coloured | [ ] |
| 10 | Region East | 2 | Utilisation 15.4%; parcels 12.3% below target | [ ] |
| 11 | Top N set to 5 | 2 | Both bar charts show 5 points (more only if utilisation ties) | [ ] |
| 12 | Right-click a point, Drill through | 3 | Point detail opens with the point's name as title | [ ] |
| 13 | Hover a point in the matrix | 2 | Tooltip with five key figures | [ ] |
| 14 | Cleaning table | 4 | 134,838 rows read, 1,237 duplicates removed, 133,601 in the fact table | [ ] |
| 15 | Unmatched point IDs | 4 | PP-091 and PP-092 | [ ] |
| 16 | Reconciliation table | 4 | All rows OK | [ ] |
| 17 | View as a regional manager (North) | all | Only North is visible; 19,976 parcels | [ ] |
| 18 | Keyboard: Tab through a page | all | Order is title, slicers, KPIs, charts | [ ] |
| 19 | The business questions Q1 to Q7 (doc 01) can all be answered | all | Yes | [ ] |
| 20 | Wording, definitions and thresholds (85%, 15%, 82%) are acceptable | doc 02 | Agreed or changed | [ ] |
