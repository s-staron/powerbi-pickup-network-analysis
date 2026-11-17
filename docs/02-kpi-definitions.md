# 02 KPI definitions

One card per KPI. The DAX measure names are the names in the model table `_Measures`. "Value" is the result for the whole data window (July 2024 to December 2025, all regions) unless a month is named; it comes from `validation/expected_results.csv`.

Conventions used by all cards:

- **Parcels** are rows of `FactParcel` after removing exact duplicates (rule R1 in doc 03).
- **Arrived** means the parcel was scanned in at a pickup point. The arrival date decides the month.
- **Ratios** use `DIVIDE`, so an empty denominator gives a blank, not an error.
- **Variance in pp** is a difference of two ratios, in percentage points.

## Volumes

### K01 Parcels Arrived

| Item | Content |
|------|---------|
| Definition | Number of parcels that arrived at a pickup point |
| Purpose | Basis for every rate; shows demand and the November-December peak |
| Formula in words | Count the rows of the parcel table in the current filter |
| DAX measure | `Parcels Arrived` |
| Grain | One parcel |
| Filters | Date, region, point, service type, sender segment, status, return reason |
| Owner | Head of Pickup Network |
| Target | `Target Parcels` per region and month (K16) |
| Value | 133,601 |
| Caveats | Includes 457 parcels at unmatched point IDs (region Unassigned). Includes parcels that were later returned. |

### K02 Parcels Collected

| Item | Content |
|------|---------|
| Definition | Parcels that a customer collected |
| Purpose | Numerator of the pickup rate |
| Formula in words | Sum of the flag "is collected" (1 when status is Collected) |
| DAX measure | `Parcels Collected` |
| Grain | One parcel |
| Filters | Same as K01 |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 126,901 |
| Caveats | None |

### K03 Parcels Returned

| Item | Content |
|------|---------|
| Definition | Parcels that went back to the sender |
| Purpose | Numerator of the return-to-sender rate |
| Formula in words | Sum of the flag "is returned" (1 when status is Returned) |
| DAX measure | `Parcels Returned` |
| Grain | One parcel |
| Filters | Same as K01; the return reason is the natural breakdown |
| Owner | Customer service lead |
| Target | None (the rate has one, K20) |
| Value | 6,700 |
| Caveats | Returned parcels have no pickup time by design (rule R3) |

### K04 Collected Within 3 Days

| Item | Content |
|------|---------|
| Definition | Parcels collected 72 hours or less after arrival |
| Purpose | Numerator of the pickup-within-3-days rate |
| Formula in words | Sum of the flag "collected and dwell time is at most 3 days" |
| DAX measure | `Collected Within 3 Days` |
| Grain | One parcel |
| Filters | Same as K01 |
| Owner | Head of Pickup Network |
| Target | None (the rate has one, K18) |
| Value | 107,131 |
| Caveats | Exactly 72 hours counts as within 3 days |

## Rates and times

### K05 Pickup Rate

| Item | Content |
|------|---------|
| Definition | Share of arrived parcels that were collected |
| Purpose | Overall success of the pickup model |
| Formula in words | Parcels Collected divided by Parcels Arrived |
| DAX measure | `Pickup Rate` |
| Grain | One parcel |
| Filters | Same as K01 |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 95.0% |
| Caveats | Because every parcel is resolved at export time, this equals 1 minus the return rate |

### K06 Pickup Within 3 Days Rate

| Item | Content |
|------|---------|
| Definition | Share of arrived parcels collected within 3 days |
| Purpose | Speed of collection; a slow pickup ties up capacity and raises return risk |
| Formula in words | Collected Within 3 Days divided by Parcels Arrived |
| DAX measure | `Pickup Within 3 Days Rate` |
| Grain | One parcel |
| Filters | Same as K01 |
| Owner | Head of Pickup Network |
| Target | 82% (K18) |
| Value | 80.2% |
| Caveats | The denominator is all arrived parcels, so returned parcels count as misses (open question OQ4) |

### K07 Return To Sender Rate

| Item | Content |
|------|---------|
| Definition | Share of arrived parcels that went back to the sender |
| Purpose | Cost and customer experience; the head of the network wants fewer returns |
| Formula in words | Parcels Returned divided by Parcels Arrived |
| DAX measure | `Return To Sender Rate` |
| Grain | One parcel |
| Filters | Same as K01 |
| Owner | Customer service lead |
| Target | 5.5% (6.5% in December); K20 |
| Value | 5.0% |
| Caveats | Lower is better. The target is weighted by planned parcels, so the network value is 5.7% for the whole window. |

### K08 Avg Dwell Days

| Item | Content |
|------|---------|
| Definition | Average days from arrival to pickup |
| Purpose | How quickly customers collect |
| Formula in words | Average of dwell days over collected parcels only |
| DAX measure | `Avg Dwell Days` |
| Grain | One parcel |
| Filters | Same as K01 |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 1.76 days |
| Caveats | Returned parcels are excluded; their dwell time ends at the return, not at a pickup |

## Capacity

### K09 Utilisation

| Item | Content |
|------|---------|
| Definition | Occupied slot-days divided by available slot-days |
| Purpose | Shows where capacity is wasted or short |
| Formula in words | Occupied: sum of dwell days of parcels at known points. Available: for each point, capacity times the days in the period on or after its opening date. Divide the first by the second. |
| DAX measure | `Utilisation` |
| Grain | Point and day; reported by point, region or period |
| Filters | Date, region, point, point type |
| Owner | Network operations |
| Target | None; flags at 85% (overloaded) and 15% (underused) |
| Value | 29.4% |
| Caveats | Dwell days are counted on the arrival date, so a parcel arriving on 31 December adds its days to December. Above 100% means demand beyond nominal capacity. Parcels at unknown points are excluded because their capacity is unknown. |

### K10 Overloaded Points

| Item | Content |
|------|---------|
| Definition | Number of points with utilisation of 85% or more in the selected period |
| Purpose | Size of the capacity problem in one number |
| Formula in words | Count the points whose Utilisation is at least 0.85 |
| DAX measure | `Overloaded Points` |
| Grain | One point |
| Filters | Date, region, point type |
| Owner | Network operations |
| Target | None |
| Value | 10 for the whole window; 19 in December 2025 |
| Caveats | The threshold is an assumption (A3). Points not yet open in the period have no utilisation and are not counted. |

## Time intelligence

The value column uses December 2025 (month filter on 2025-12).

### K11 Parcels MTD

| Item | Content |
|------|---------|
| Definition | Parcels arrived from the first day of the month to the last selected date |
| Purpose | Month progress |
| Formula in words | Parcels Arrived over the month-to-date dates |
| DAX measure | `Parcels MTD` |
| Grain | One day |
| Filters | Date |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 12,047 for December 2025 |
| Caveats | For a complete month it equals the month total |

### K12 Parcels YTD

| Item | Content |
|------|---------|
| Definition | Parcels arrived from 1 January to the last selected date |
| Purpose | Year progress |
| Formula in words | Parcels Arrived over the year-to-date dates |
| DAX measure | `Parcels YTD` |
| Grain | One day |
| Filters | Date |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 89,451 at the end of December 2025 |
| Caveats | Data starts in July 2024, so the 2024 year-to-date covers only July to December |

### K13 Parcels PY

| Item | Content |
|------|---------|
| Definition | Parcels arrived in the same period one year earlier |
| Purpose | Basis for year-on-year change |
| Formula in words | Parcels Arrived shifted back one year |
| DAX measure | `Parcels PY` |
| Grain | One day |
| Filters | Date |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 10,141 for December 2024 |
| Caveats | Blank for dates before July 2025 because there is no earlier year |

### K14 Parcels YoY %

| Item | Content |
|------|---------|
| Definition | Change in parcels versus the same period one year earlier |
| Purpose | Growth |
| Formula in words | (Parcels Arrived minus Parcels PY) divided by Parcels PY |
| DAX measure | `Parcels YoY %` |
| Grain | One day |
| Filters | Date |
| Owner | Head of Pickup Network |
| Target | None |
| Value | +18.8% for December 2025 |
| Caveats | Part of the growth comes from six points that opened during the data window |

### K15 Parcels Rolling 3M

| Item | Content |
|------|---------|
| Definition | Parcels arrived in the three months ending on the last selected date |
| Purpose | Smooths weekly and month noise |
| Formula in words | Parcels Arrived over the last 3 months |
| DAX measure | `Parcels Rolling 3M` |
| Grain | One day |
| Filters | Date |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 29,388 for October to December 2025 |
| Caveats | At the start of the data (July and August 2024) fewer than 3 months exist |

## Targets and variance

### K16 Target Parcels

| Item | Content |
|------|---------|
| Definition | Planned parcel volume |
| Purpose | Benchmark for volume |
| Formula in words | Sum of the monthly regional targets in the filter |
| DAX measure | `Target Parcels` |
| Grain | One region and one month |
| Filters | Region, month |
| Owner | Head of Pickup Network |
| Target | Is the target |
| Value | 138,670 |
| Caveats | Blank when the selection is narrowed to single points. A partial month selection still adds whole-month targets. |

### K17 Parcels vs Target %

| Item | Content |
|------|---------|
| Definition | Actual parcels minus target, divided by target |
| Purpose | Shows who is behind plan |
| Formula in words | (Parcels Arrived minus Target Parcels) divided by Target Parcels |
| DAX measure | `Parcels vs Target %` |
| Grain | One region and one month |
| Filters | Region, month |
| Owner | Head of Pickup Network |
| Target | 0% |
| Value | -3.7% (East -12.3%, North -0.2%) |
| Caveats | At network level the actuals include Unassigned parcels, the targets do not |

### K18 Target Pickup Within 3 Days Rate

| Item | Content |
|------|---------|
| Definition | Planned share of parcels collected within 3 days |
| Purpose | Benchmark for K06 |
| Formula in words | Average of the monthly regional targets weighted by planned parcels |
| DAX measure | `Target Pickup Within 3 Days Rate` |
| Grain | One region and one month |
| Filters | Region, month |
| Owner | Head of Pickup Network |
| Target | Is the target (82% in every region and month) |
| Value | 82.0% |
| Caveats | Blank at point level |

### K19 Pickup 3D vs Target pp

| Item | Content |
|------|---------|
| Definition | Pickup-within-3-days rate minus its target, in percentage points |
| Purpose | Shows who is too slow |
| Formula in words | K06 minus K18; blank when there is no target |
| DAX measure | `Pickup 3D vs Target pp` |
| Grain | One region and one month |
| Filters | Region, month |
| Owner | Head of Pickup Network |
| Target | 0 pp or higher |
| Value | -1.8 pp (West -12.3 pp, Central +1.3 pp) |
| Caveats | Negative means the target is missed |

### K20 Target Return Rate

| Item | Content |
|------|---------|
| Definition | Planned return-to-sender rate |
| Purpose | Benchmark for K07 |
| Formula in words | Average of the monthly regional targets weighted by planned parcels |
| DAX measure | `Target Return Rate` |
| Grain | One region and one month |
| Filters | Region, month |
| Owner | Customer service lead |
| Target | Is the target (5.5%, 6.5% in December) |
| Value | 5.7% |
| Caveats | Lower is better, so an actual below the target is good. Blank at point level. |

## Shares and ranking

### K21 Parcels % of Network

| Item | Content |
|------|---------|
| Definition | Share of all parcels of the network |
| Purpose | Weight of a region or point |
| Formula in words | Parcels Arrived divided by Parcels Arrived with the region and point filters removed (`ALL`) |
| DAX measure | `Parcels % of Network` |
| Grain | One parcel |
| Filters | Date stays; region and point filters are removed in the denominator |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 100% at network level |
| Caveats | `ALL` ignores slicers. Under row-level security the "network" is the regions the user may see. |

### K22 Parcels % of Selection

| Item | Content |
|------|---------|
| Definition | Share of what the slicers select |
| Purpose | Weight inside the current view |
| Formula in words | Parcels Arrived divided by Parcels Arrived with the visual's own row filters removed but slicer filters kept (`ALLSELECTED`) |
| DAX measure | `Parcels % of Selection` |
| Grain | One parcel |
| Filters | Slicers stay; the visual's rows are removed in the denominator |
| Owner | Head of Pickup Network |
| Target | None |
| Value | 100% for the whole selection; a region's share is its parcels divided by 133,601 |
| Caveats | Changes when a region slicer is used; K21 does not |

### K23 Top N Utilisation, Bottom N Utilisation, Top N Value

| Item | Content |
|------|---------|
| Definition | Utilisation of a point if it is among the N most (or least) utilised points of the selection, otherwise blank; N is chosen with a slicer (3 to 15, default 10) |
| Purpose | Shortlist of points to act on |
| Formula in words | Rank known points by Utilisation with `RANKX`; show the value when the rank is at most N |
| DAX measure | `Top N Utilisation`, `Bottom N Utilisation`, `Top N Value` |
| Grain | One point |
| Filters | Date, region, point type |
| Owner | Network operations |
| Target | None |
| Value | Depends on N and the selection |
| Caveats | Ties share a rank (dense ranking), so slightly more than N points can show. Points not open in the period are excluded. |

## Support measures

These are not KPIs; they exist so the report can show titles, colours and checks.

| Measure | Purpose |
|---------|---------|
| `Title Overview` | Dynamic page title with region and period |
| `Title Point Detail` | Dynamic title of the drill-through page |
| `Utilisation Color` | Cell colour for conditional formatting (red 85% or more, amber under 15%) |
| `Check Actual` | Model value for the current row of the expected-results table |
| `Check Status` | OK or CHECK per reconciliation row |

The model has 30 measures in total: 25 KPI measures in the cards above (K23 covers three) and 5 support measures.

## Reference: KPI values by region (whole window)

| Region | Parcels | vs target | Pickup within 3 days | vs target | Return rate | Avg dwell days | Utilisation | Overloaded points |
|--------|--------:|----------:|---------------------:|----------:|------------:|---------------:|------------:|------------------:|
| Central | 54,761 | -2.6% | 83.3% | +1.3 pp | 4.8% | 1.57 | 39.1% | 3 |
| South | 27,672 | -5.2% | 80.7% | -1.3 pp | 5.0% | 1.74 | 26.0% | 3 |
| West | 20,579 | -4.9% | 69.7% | -12.3 pp | 6.3% | 2.31 | 29.4% | 3 |
| North | 19,976 | -0.2% | 80.5% | -1.5 pp | 4.5% | 1.78 | 29.1% | 1 |
| East | 10,156 | -12.3% | 83.1% | +1.1 pp | 4.7% | 1.60 | 15.4% | 0 |
| Unassigned | 457 | n/a | 75.1% | n/a | 6.8% | 2.18 | n/a | n/a |
| **Network** | **133,601** | **-3.7%** | **80.2%** | **-1.8 pp** | **5.0%** | **1.76** | **29.4%** | **10** |
