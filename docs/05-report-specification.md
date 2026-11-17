# 05 Report specification

The report is stored as PBIR in `PickupNetwork.Report/definition/`. Canvas size is 1280 by 720 pixels, "fit to page". The look comes from one theme file, `StaticResources/RegisteredResources/PickupNetworkTheme.json`.

## 1. Design rules

| Topic | Rule |
|-------|------|
| Theme | One theme file; no per-visual colours except the conditional formatting colours that come from a measure |
| Palette | Colour-blind-safe (blue `#0072B2`, orange `#E69F00`, green `#009E73`, pink `#CC79A7`, sky `#56B4E9`, vermilion `#D55E00`, grey `#5F6B7A`, indigo `#332288`) on a white background; text `#1F2933` |
| Colour as a signal | Never the only signal: the number is always shown; the legend names the colours |
| Alt text | Every visual has alt text that says what it shows |
| Reading order | `tabOrder` follows the visual order on the page: title, slicers, KPIs, charts |
| Titles | Every visual has a title; page and drill-through titles are dynamic |
| Pages | 4 visible pages and 1 hidden tooltip page |

Page order: Executive overview, Network performance, Point detail (drill-through target), Data quality and reconciliation. The tooltip page is last and hidden in view mode.

## 2. Page 1: Executive overview

| | |
|--|--|
| Purpose | Judge the network in one minute: volume, pickup speed, returns, capacity |
| Audience | Head of the pickup network |
| Questions | Q1, Q3, Q4, Q5, Q6 |

Layout (top to bottom):

| Visual | Type | Fields | Notes |
|--------|------|--------|-------|
| Page title | Card | `Title Overview` | Dynamic: region and period |
| Region slicer | Slicer, dropdown | `DimRegion[Region]` | Synced with the Network page |
| Month slicer | Slicer, dropdown | `DimDate[YearMonth]` | Synced with the Network page |
| Headline KPI slicer | Slicer, dropdown | `Headline KPI[Headline KPI]` | Field parameter: pickup within 3 days, return rate, utilisation, parcels, dwell days |
| KPI: Parcels arrived | Multi-row card | `Parcels Arrived`, `Parcels vs Target %`, `Parcels YoY %` | Target and last-year comparison |
| KPI: Pickup within 3 days | Multi-row card | `Pickup Within 3 Days Rate`, `Target Pickup Within 3 Days Rate`, `Pickup 3D vs Target pp` | |
| KPI: Return to sender | Multi-row card | `Return To Sender Rate`, `Target Return Rate`, `Parcels Returned` | Lower is better |
| KPI: Capacity | Multi-row card | `Utilisation`, `Overloaded Points`, `Avg Dwell Days` | |
| Headline KPI by month | Line chart | `DimDate[YearMonth]`, field parameter `Headline KPI Fields` | Switches with the slicer |
| Pickup within 3 days vs target, by region | Clustered bar | `DimRegion[Region]`, `Pickup Within 3 Days Rate`, `Target Pickup Within 3 Days Rate` | Sorted by rate, descending |
| Parcels arrived vs same month last year | Clustered column | `DimDate[YearMonth]`, `Parcels Arrived`, `Parcels PY` | Shows the peak; the previous year starts in July 2025 |
| Why parcels go back to the sender | Clustered bar | `FactParcel[ReturnReason]`, `Parcels Returned` | Sorted descending |

Interactions: the slicers filter every visual on the page. Clicking a bar cross-filters the other charts (default interactions). Region and month selections carry over to page 2.

Filters: none on the page itself.

## 3. Page 2: Network performance

| | |
|--|--|
| Purpose | Find the regions and points that are overloaded, underused or off target |
| Audience | Head of the network, operations, regional managers |
| Questions | Q2, Q3, Q5, Q6 |

| Visual | Type | Fields | Notes |
|--------|------|--------|-------|
| Page title | Text box | Static | |
| Region slicer | Slicer | `DimRegion[Region]` | Synced with page 1 (sync group `RegionSlicer`) |
| Month slicer | Slicer | `DimDate[YearMonth]` | Synced with page 1 (sync group `MonthSlicer`) |
| Point type slicer | Slicer | `DimPickupPoint[PointType]` | Page only |
| Top N slicer | Slicer | `Top N[Top N]` | 3 to 15, default 10 |
| Region and point performance | Matrix | Rows: `DimRegion[Region]` then `DimPickupPoint[PointName]`. Values: `Parcels Arrived`, `Parcels % of Selection`, `Parcels vs Target %`, `Pickup Within 3 Days Rate`, `Pickup 3D vs Target pp`, `Return To Sender Rate`, `Avg Dwell Days`, `Utilisation` | Utilisation cell background from `Utilisation Color` (red 85% or more, amber under 15%). Expand a region to see its points. |
| Legend | Text box | Static | Names the colours |
| Most utilised points (Top N) | Clustered bar | `DimPickupPoint[PointName]`, `Top N Utilisation` | Sorted descending |
| Least utilised points (Bottom N) | Clustered bar | `DimPickupPoint[PointName]`, `Bottom N Utilisation` | Sorted ascending |

Interactions:

- Right-click a point in the matrix or in a bar chart, then Drill through, then Point detail.
- Hover a point in the matrix or in a bar chart: the tooltip page shows its key figures.
- Target columns are blank on point rows and when a point type is chosen, because targets exist per region only.

## 4. Page 3: Point detail (drill-through target)

| | |
|--|--|
| Purpose | Look at one point: speed, returns, rhythm, attributes |
| Audience | Regional managers, operations |
| Questions | Q3, Q4, Q6 |
| Drill-through field | `DimPickupPoint[PointName]` (page filter `filter_point`) |

| Visual | Type | Fields |
|--------|------|--------|
| Page title | Card | `Title Point Detail` (dynamic, shows the point name) |
| Five cards | Card | `Parcels Arrived`, `Pickup Within 3 Days Rate`, `Return To Sender Rate`, `Utilisation`, `Avg Dwell Days` |
| Parcels per month vs last year | Line chart | `DimDate[YearMonth]`, `Parcels Arrived`, `Parcels PY` |
| Weekly rhythm | Clustered column | `DimDate[WeekdayName]`, `Parcels Arrived` |
| Returns by reason | Clustered bar | `FactParcel[ReturnReason]`, `Parcels Returned` |
| Point attributes | Table | `PointName`, `PointType`, `City`, `PartnerCategory`, `Capacity`, `OpeningDate` |

Opened without drill-through, the page shows all points and the title says so.

## 5. Page 3b: Point tooltip (hidden)

Size 320 by 240. Page type Tooltip, hidden in view mode. One multi-row card with `Parcels Arrived`, `Pickup Within 3 Days Rate`, `Return To Sender Rate`, `Utilisation`, `Avg Dwell Days`. It is attached to the matrix and to both Top N and Bottom N charts on page 2.

## 6. Page 4: Data quality and reconciliation

| | |
|--|--|
| Purpose | Show what was cleaned and prove that the model equals the source |
| Audience | Head of the network, analysts, auditors |
| Questions | Q7 |

| Visual | Type | Fields |
|--------|------|--------|
| Page title | Text box | Static |
| Rows per cleaning step | Table | `DQ_Cleaning[StepOrder]`, `DataSet`, `Step`, `Rows`, `Handling` |
| Unmatched point IDs | Table | `DQ_UnmatchedPoints[SourcePointId]`, `ParcelRows` |
| Explanation | Text box | Static: how unmatched points and the reconciliation work |
| Model vs expected totals | Table | `ExpectedResults[KpiId]`, `Scope`, `ScopeValue`, `ExpectedValue`, `Check Actual`, `Check Status` |

The reconciliation table has 149 rows: KPIs for the network, each region (and Unassigned), September and December 2025, and the data-quality counts. `Check Status` is OK when the model value equals the expected value within 0.000001.

## 7. Slicer sync and filter scope

| Slicer | Pages | Sync group |
|--------|-------|-----------|
| Region | Executive overview, Network performance | `RegionSlicer` |
| Month | Executive overview, Network performance | `MonthSlicer` |
| Headline KPI | Executive overview | none |
| Point type, Top N | Network performance | none |

The sync is stored in each slicer's `syncGroup`. In Power BI Desktop, open View, Sync slicers to see which pages each group appears on; the Point detail page is not part of either group because the drill-through supplies its own filter.

## 8. Known limitations

- Pages are laid out for desktop; there is no phone layout.
- The headline line chart uses a field parameter that I wrote by hand in PBIR. If Power BI Desktop shows an error on that visual, remove the field and add the `Headline KPI Fields` column again.
- The matrix is wide; at a small window the user scrolls.
