# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-11-17

### Fixed

- Power BI Desktop could not open the project because a description comment stood above a table permission in the row-level security role. The description now describes the role.
- Tab order was reversed (PBIR focuses the highest value first). The page title now has the highest value, so the keyboard follows the reading order.

### Added

- `validation/tmdl_parse_check.ps1`: loads the TMDL with the serializer of the installed Power BI Desktop.
- Validator rules for description placement and tab-order direction (582 checks).

## [1.0.0] - 2026-11-17

### Added

- Seeded generator for synthetic parcel, pickup point and target data (`scripts/generate_data.py`) and the generated raw files for seed 42.
- Power BI Project (PBIP) with a TMDL semantic model and a PBIR report.
- Power Query: `DataFolder` parameter, staging queries, M functions, one named step for each of the quality rules R1 to R6, a date table.
- Star-schema model with hidden keys, a marked date table and 30 documented DAX measures.
- Field parameter `Headline KPI`, parameter table `Top N`, dynamic titles and conditional colour.
- Row-level security role `Regional Manager` with a user-region mapping table.
- Report pages: Executive overview, Network performance, Point detail (drill-through), Data quality and reconciliation, and a hidden tooltip page; one theme.
- `validation/reconcile.py`, `validation/expected_results.csv`, `validation/sql_crosscheck.py` and `validation/validate_project.py`.
- Documentation: business requirements, KPI definitions, data dictionary and lineage, data model, report specification, test and reconciliation report, release notes.

### Known issues

- Power Query, DAX and row-level security have not been run in Power BI Desktop yet (see `docs/06-test-and-reconciliation-report.md`).
