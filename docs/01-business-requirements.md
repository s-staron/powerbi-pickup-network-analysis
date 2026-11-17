# 01 Business requirements

Project: Pickup network analysis for Norvane Parcel
Version: 1.0
Status: delivered, ready for UAT

> **Synthetic data.** Norvane Parcel is a fictional company. A web search for the name found no carrier or parcel brand with it. All data comes from `scripts/generate_data.py`. Where the carrier's rules are not public, this document states an assumption (section 9).

## 1. Background

Norvane Parcel delivers parcels to customers who collect them from a network of **pickup points**:

- **Parcel shops**: a partner business (pharmacy, newsagent, convenience store, petrol station) keeps parcels behind the counter during opening hours.
- **Parcel lockers**: self-service units, open around the clock, usually at a supermarket car park, residential estate, transport hub or petrol station.

Parcels that are not collected within the storage period go back to the sender. The network has 90 active points in 5 regions (data window: July 2024 to December 2025). The head of the network gets monthly numbers from the source system exports but has no single view of where capacity is wasted, where it is short, how fast customers collect, and why parcels are returned.

## 2. Problem statement

The head of the pickup network cannot answer four recurring questions without asking an analyst for an extract:

1. Where is the network underused and where is it overloaded?
2. How fast do customers collect their parcels?
3. Why do parcels go back to the sender?
4. Which points and regions miss their targets?

## 3. Objectives

| ID | Objective | Measured by |
|----|-----------|-------------|
| O1 | Give the head of the network one report that answers the four questions | Report passes UAT checklist (doc 06, section 7) |
| O2 | Make every KPI traceable and agreed | One card per KPI in doc 02, with owner and DAX measure |
| O3 | Make numbers trustworthy | All KPIs reconcile to values recomputed from the raw files (doc 06) |
| O4 | Let regional managers see only their region | Row-level security role tested (doc 06) |
| O5 | Keep the project maintainable | PBIP/TMDL/PBIR in Git, one parameter to open on any machine |

## 4. Stakeholders and RACI

| Role | Interest |
|------|----------|
| Head of Pickup Network | Decision maker; main report user; accountable for network KPIs |
| Regional managers (5) | See their own region; act on weak points |
| Network operations team | Fix overloaded and underused points |
| Customer service lead | Interested in return reasons and pickup speed |
| Source-system owner | Provides the parcel, point and target exports; fixes data issues at source |
| Business data analyst (author) | Builds the model and report, documents and tests them |

RACI: R = responsible, A = accountable, C = consulted, I = informed.

| Activity | Head of Network | Regional managers | Ops team | Source-system owner | Analyst |
|----------|:---:|:---:|:---:|:---:|:---:|
| Define KPIs and targets | A | C | C | I | R |
| Provide and fix source exports | I | I | I | A/R | C |
| Build model and report | I | I | I | C | A/R |
| Validate numbers (UAT) | A | R | C | C | R |
| Act on findings | A | R | R | I | C |
| Maintain report after release | I | I | I | C | A/R |

## 5. Scope

In scope:

- Parcels that arrived at a pickup point between 1 July 2024 and 31 December 2025.
- Pickup points of type parcel shop and parcel locker.
- KPIs for volume, pickup speed, returns, dwell time and capacity utilisation.
- Monthly targets per region for volume, pickup within 3 days and return rate.
- Region-based row-level security.
- A data quality and reconciliation page.

Out of scope:

- Home delivery and parcels that never reach a pickup point.
- Revenue, cost and customer-level analysis.
- Forecasting and what-if modelling of new points.
- Targets per single point.
- Live refresh from a database (v1.0 reads CSV exports).
- Publishing to the Power BI service and scheduled refresh.

## 6. Business questions

| ID | Question | Answered on |
|----|----------|-------------|
| Q1 | How many parcels arrive, versus target and versus last year? | Executive overview |
| Q2 | Which regions and points are overloaded (85% or more) or underused (under 15%)? | Network performance |
| Q3 | What share of parcels is collected within 3 days, and how long do parcels stay? | Executive overview, Network performance |
| Q4 | Why do parcels go back to the sender? | Executive overview, Point detail |
| Q5 | Which regions miss volume, pickup-speed or return targets? | Executive overview, Network performance |
| Q6 | How strong is the weekly rhythm and the November-December peak? | Executive overview, Point detail |
| Q7 | Can I trust these numbers? | Data quality and reconciliation |

## 7. User stories and acceptance criteria

**US1. Network health at a glance.**
As the head of the network, I want headline KPIs with target and last-year comparison, so that I can judge the month in one minute.

- Given the report opens on the Executive overview, When no filter is set, Then I see parcels arrived, pickup within 3 days, return rate and utilisation for the whole data window, with variance to target.
- Given I select December 2025 in the month slicer, When the page refreshes, Then the title names the month and the KPIs show December values, with the year-on-year change in parcels.

**US2. Find overloaded and underused points.**
As the head of the network, I want to rank points by utilisation, so that operations can move capacity.

- Given the Network performance page, When I set Top N to 10, Then the two bar charts show the 10 most and 10 least utilised points of the current selection.
- Given a point has utilisation of 85% or more, When it appears in the matrix, Then its utilisation cell is coloured and the legend explains the colour.

**US3. Compare regions with targets.**
As the head of the network, I want each region's actual versus target, so that I know who misses.

- Given the matrix shows regions, When I look at a region row, Then parcels versus target, pickup within 3 days versus target and the variance are visible.
- Given I narrow the selection to single points, When targets do not exist at point level, Then the target measures are blank, not wrong.

**US4. Understand returns.**
As the customer service lead, I want return reasons, so that I can target the main cause.

- Given the Executive overview, When I read the return-reason chart, Then reasons are sorted by number of returned parcels.
- Given I drill through to a point, When the Point detail page opens, Then the return reasons show only that point.

**US5. Look at one point.**
As a regional manager, I want a detail page for one point, so that I can talk to the partner.

- Given the matrix lists points, When I right-click a point and choose Drill through, Then the Point detail page opens filtered to that point, with its title showing the point name.
- Given the page is open, When I hover a point in a chart on the Network page, Then a tooltip shows its key figures.

**US6. Regional security.**
As a regional manager, I must see only my region.

- Given my e-mail is mapped to the region North in the mapping table, When I open the report, Then only North appears in slicers, visuals and totals.
- Given my e-mail is not in the mapping table, When I open the report, Then no region data is shown.

**US7. Trust the numbers.**
As the head of the network, I want to know what was cleaned and whether totals match the source, so that I can rely on the report.

- Given the Data quality page, When I read the cleaning table, Then each issue shows its row count and how it was handled.
- Given the reconciliation table, When every status shows OK, Then the model equals the values recomputed from the raw files.

## 8. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NF1 | Opens on any machine after setting one parameter (`DataFolder`) and refreshing |
| NF2 | Refresh of the 134,838 parcel export rows completes in well under a minute on a laptop (not measured in v1.0) |
| NF3 | Star schema, single-direction one-to-many relationships, marked date table |
| NF4 | Accessible: colour-blind-safe palette, alt text on every visual, tab order, colour never the only signal |
| NF5 | One theme file for the whole report |
| NF6 | Source control friendly: PBIP, TMDL and PBIR text files, no binary `.pbix` |
| NF7 | Security by region with row-level security; DQ tables hidden from the role |
| NF8 | Every KPI has one definition, one measure and one owner (doc 02) |

## 9. Assumptions

| ID | Assumption (public, general knowledge of pickup networks; not Norvane facts) |
|----|-------------|
| A1 | Parcels are stored 7 days; after that the carrier takes them back for return to sender. |
| A2 | "Pickup within 3 days" (72 hours after arrival) is the speed target; the target value of 82% is invented. |
| A3 | Utilisation of 85% or more means overloaded; under 15% means underused. Thresholds are invented. |
| A4 | Capacity is measured in parcel slots. A parcel occupies one slot from arrival until pickup or return. |
| A5 | Every parcel is resolved (collected or returned) by the export date, 15 January 2026. |
| A6 | Targets are monthly, per region. They are synthetic, generated as a plan around actual volumes. |
| A7 | Timestamps are in one local time zone; daylight saving shifts are ignored. |
| A8 | The pickup rate counts collected parcels over all arrived parcels. |

## 10. Open questions

| ID | Question | Owner | Impact if answered differently |
|----|----------|-------|--------------------------------|
| OQ1 | Is the storage period really 7 days for all service types? | Network operations | Changes what "overdue" means and the return logic |
| OQ2 | Is capacity in slots or in simultaneous parcels? | Network operations | Changes the utilisation denominator |
| OQ3 | Should utilisation use the daily peak instead of the average? | Head of network | Peak days would show more overloaded points |
| OQ4 | Should a return before the storage period ended count as a pickup failure? | Customer service | Changes the pickup-within-3-days denominator |
| OQ5 | Should parcels at unknown points stay in totals? | Source-system owner | v1.0 keeps them as Unassigned (457 of 133,601 parcels) |
| OQ6 | Are targets also needed per point? | Head of network | Needs a new target table and measures |
