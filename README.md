# Pickup Network Analysis (Power BI)

A Power BI report for the head of the pickup-point network of **Norvane Parcel**, a fictional parcel carrier. It shows where the network is underused or overloaded, how fast customers collect their parcels, why parcels go back to the sender, and which regions and points miss their targets.

> **All data in this repository is synthetic.** It is produced by a seeded Python script (`scripts/generate_data.py`). Norvane Parcel, its points, regions, targets and numbers are invented; no real carrier's data is used. A web search found no carrier or parcel brand named Norvane at the time of writing (17 November 2026).

## Business problem

Norvane Parcel delivers to 90 pickup points: parcel shops (partner businesses) and parcel lockers. A parcel that is not collected within the storage period goes back to the sender. The head of the network gets exports but no single view of capacity, pickup speed, returns and targets. The report answers four questions:

1. Where is the network underused, and where is it overloaded?
2. How fast do customers collect their parcels?
3. Why do parcels go back to the sender?
4. Which points and regions miss their targets?

## What the report shows (synthetic results, July 2024 to December 2025)

| Finding | Number |
|---------|-------:|
| Parcels arrived | 133,601 (3.7% below the plan of 138,670) |
| Collected within 3 days | 80.2% (target 82.0%) |
| Returned to sender | 5.0% (target 5.7%) |
| Capacity utilisation | 29.4%; 10 points at 85% or more |
| Region West, collected within 3 days | 69.7%, which is 12.3 percentage points below target |
| Region East, utilisation | 15.4%, parcels 12.3% below plan |
| December 2025 | 12,047 parcels, +18.8% on December 2024, 19 overloaded points |

All numbers are from `validation/expected_results.csv`, computed from the raw files outside Power BI.

## Screenshots

Screenshots are added after the report has been opened in Power BI Desktop (see "Status of verification").

| Page | File to add |
|------|-------------|
| Executive overview | `docs/images/01-executive-overview.png` _(to be added)_ |
| Network performance | `docs/images/02-network-performance.png` _(to be added)_ |
| Point detail | `docs/images/03-point-detail.png` _(to be added)_ |
| Data quality and reconciliation | `docs/images/04-data-quality.png` _(to be added)_ |

## Repository structure

```text
PickupNetwork.pbip                  Power BI Project entry point
PickupNetwork.SemanticModel/        Semantic model in TMDL
  definition/expressions.tmdl         DataFolder parameter, M functions, staging queries
  definition/tables/*.tmdl            tables, columns, measures, partitions (Power Query)
  definition/relationships.tmdl       star-schema relationships
  definition/roles/                   row-level security role
PickupNetwork.Report/               Report in PBIR (one JSON file per page and visual)
  StaticResources/RegisteredResources/PickupNetworkTheme.json   the one theme
data/raw/                           synthetic exports: parcels, points, targets
data/reference/                     city mapping, user-region mapping (RLS)
scripts/generate_data.py            seeded generator for the synthetic data
validation/                         reconcile.py, expected_results.csv, sql_crosscheck.py, validate_project.py
docs/                               01 requirements ... 07 release notes
CHANGELOG.md
```

## How to open

1. Install **Power BI Desktop for Windows**, a current monthly release. Projects (PBIP) with TMDL and PBIR need a release that supports them; if Desktop reports a format error, update it.
2. Clone the repository.
3. Open `PickupNetwork.pbip`.
4. **Home, Transform data, Edit parameters**: set **`DataFolder`** to the path of the cloned repository (the folder that contains `data\` and `validation\`), without a trailing backslash. Click OK, then **Close & Apply**.
5. **Refresh**. Open page 4, "Data quality and reconciliation": every row of the reconciliation table should show **OK**.

No data is stored in the project; the model is rebuilt from the CSV files on refresh.

### Optional: regenerate and check the data

```bash
python scripts/generate_data.py          # same seed gives byte-identical files
python validation/reconcile.py           # recompute expected_results.csv
python validation/sql_crosscheck.py      # the same KPIs again, in SQL (SQLite)
pip install jsonschema referencing
python validation/validate_project.py    # schemas, TMDL, PBIR, references
```

## Status of verification

The project was built without the Power BI Modeling MCP, and Power BI Desktop could not be driven from a script. The files are checked statically (50 JSON files against Microsoft's schemas, 577 checks of the TMDL and PBIR structure, 0 failed) and the expected numbers were computed twice (Python and SQL, 86 values, 0 differences). **Power Query and DAX have not been executed yet**: the reconciliation page does that the first time the file is refreshed in Desktop. Details and a UAT checklist: [`docs/06-test-and-reconciliation-report.md`](docs/06-test-and-reconciliation-report.md).

## File formats: GA or preview?

Checked on 17 November 2026 against Microsoft documentation.

| Format | Status | Source |
|--------|--------|--------|
| Power BI Project (PBIP) | Generally available | [Edit Power BI Desktop project files outside Power BI Desktop](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-external-editing) |
| Power BI enhanced report format (PBIR) | Generally available; the default report format of Power BI | [Power BI Desktop project report folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report) |
| Tabular Model Definition Language (TMDL) | Generally available | Power BI blog "Announcing general availability of Tabular Model Definition Language (TMDL)"; [TMDL overview](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview) |

Caveat: some older or translated pages still describe PBIR as a preview, and the release notes show that making PBIR the default in Desktop was rolled out in stages. Check the current release notes if Desktop behaves differently.

## Documentation

| Document | Content |
|----------|---------|
| [01 Business requirements](docs/01-business-requirements.md) | Background, stakeholders and RACI, scope, user stories with acceptance criteria, assumptions, open questions |
| [02 KPI definitions](docs/02-kpi-definitions.md) | One card per KPI: definition, formula, DAX measure, grain, owner, target, caveats |
| [03 Data dictionary and lineage](docs/03-data-dictionary-and-lineage.md) | Tables, columns, lineage diagram, data quality issues and handling |
| [04 Data model](docs/04-data-model.md) | Star schema, relationships, date table, row-level security |
| [05 Report specification](docs/05-report-specification.md) | Pages, visuals, interactions, drill-through, tooltips |
| [06 Test and reconciliation report](docs/06-test-and-reconciliation-report.md) | Test cases, how each was run, defects, UAT checklist |
| [07 Release notes](docs/07-release-notes.md) | Version 1.0.0 |

## License and author

Author: s-staron. Portfolio project on synthetic data.
