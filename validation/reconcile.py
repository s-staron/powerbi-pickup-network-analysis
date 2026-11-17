#!/usr/bin/env python3
"""Recompute every report KPI straight from the raw CSV exports.

This is the independent check of the Power BI model: it reads data/raw and
data/reference, applies the documented cleaning rules (docs/03-data-dictionary-
and-lineage.md) and writes validation/expected_results.csv.  The report's
"Data quality and reconciliation" page loads that file and compares each row
with the live measure.

Cleaning rules (same order as the Power Query staging queries)
  R1  Exact duplicate rows in parcels_export.csv are removed (all 9 columns equal).
  R2  Timestamps come in two formats: yyyy-MM-dd HH:mm:ss and dd.MM.yyyy HH:mm:ss.
  R3  Empty text and the text 'NULL' in pickup_ts / return_ts mean "no value".
  R4  A point_id that is not in the points table is kept and mapped to PP-UNKNOWN
      (region 'Unassigned', capacity 0).
  R5  City spelling is standardised with data/reference/city_mapping.csv
      (key = trimmed, lower-cased text).
  R6  opening_date comes in two formats: yyyy-MM-dd and dd.MM.yyyy.

Run:  python validation/reconcile.py
"""
from __future__ import annotations

import calendar
import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
OUT = Path(__file__).resolve().parent / "expected_results.csv"

UNKNOWN_ID = "PP-UNKNOWN"
UNKNOWN_REGION = "Unassigned"
OVERLOAD_THRESHOLD = 0.85
UNDERUSE_THRESHOLD = 0.15   # used for the "Underused" flag in the report, not for a KPI
MONTH_SCOPES = ["2025-09", "2025-12"]


# ---------------------------------------------------------------- parsing (R2, R3, R6)
def parse_ts(text: str):
    text = text.strip()
    if text == "" or text.upper() == "NULL":
        return None
    fmt = "%d.%m.%Y %H:%M:%S" if "." in text else "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(text, fmt)


def parse_open(text: str) -> date:
    text = text.strip()
    return datetime.strptime(text, "%d.%m.%Y" if "." in text else "%Y-%m-%d").date()


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- load and clean
def load():
    city_map = {r["city_key"]: r["city"] for r in read_csv(REF / "city_mapping.csv")}

    points, city_variants, dotted_open = {}, 0, 0
    for r in read_csv(RAW / "pickup_points_export.csv"):
        key = r["city"].strip().lower()
        canonical = city_map[key]                     # KeyError = unmapped spelling (a defect)
        city_variants += r["city"] != canonical
        dotted_open += "." in r["opening_date"]
        points[r["point_id"]] = {
            "name": r["point_name"], "type": r["point_type"], "region": r["region"], "city": canonical,
            "capacity": int(r["capacity_slots"]), "opening": parse_open(r["opening_date"]),
        }

    raw_rows = [tuple(r.values()) for r in read_csv(RAW / "parcels_export.csv")]   # R1 input
    distinct = list(dict.fromkeys(raw_rows))                                       # R1
    fact, non_iso, returned_no_pickup = [], 0, 0
    unmatched_rows, unmatched_ids = 0, defaultdict(int)
    for (pid, point_id, arr, pick, ret, status, reason, service, segment) in distinct:
        non_iso += "." in arr
        arrival, pickup, ret_ts = parse_ts(arr), parse_ts(pick), parse_ts(ret)
        returned_no_pickup += status == "Returned" and pickup is None
        if point_id not in points:                                                  # R4
            unmatched_rows += 1
            unmatched_ids[point_id] += 1
            point_key, region = UNKNOWN_ID, UNKNOWN_REGION
        else:
            point_key, region = point_id, points[point_id]["region"]
        end = pickup if status == "Collected" else ret_ts
        dwell = (end - arrival).total_seconds() / 86400.0
        fact.append({
            "arrival": arrival, "month": arrival.strftime("%Y-%m"), "point": point_key, "region": region,
            "collected": status == "Collected", "returned": status == "Returned", "dwell": dwell,
            "within3": status == "Collected" and dwell <= 3.0,
        })

    targets = [{"region": r["region"], "month": r["month"][:7], "parcels": int(r["target_parcels"]),
                "pickup3d": float(r["target_pickup_3d_rate"]), "ret": float(r["target_return_rate"])}
               for r in read_csv(RAW / "monthly_targets_export.csv")]

    dq = {
        "dq_raw_rows": len(raw_rows),
        "dq_duplicates_removed": len(raw_rows) - len(distinct),
        "dq_rows_after_dedupe": len(distinct),
        "dq_non_iso_timestamp_rows": non_iso,
        "dq_returned_without_pickup": returned_no_pickup,
        "dq_unmatched_point_rows": unmatched_rows,
        "dq_rows_in_fact": len(fact),
        "dq_points_raw_rows": len(points),
        "dq_point_city_variants": city_variants,
        "dq_point_dotted_opening_dates": dotted_open,
        "dq_unmatched_point_ids": len(unmatched_ids),
    }
    return points, fact, targets, dq, dict(unmatched_ids)


# ---------------------------------------------------------------- KPI maths
def days_in(months):
    """All calendar days of the given 'YYYY-MM' months, as a list of dates."""
    out = []
    for m in months:
        y, mo = int(m[:4]), int(m[5:])
        out += [date(y, mo, d) for d in range(1, calendar.monthrange(y, mo)[1] + 1)]
    return out


def all_months(fact):
    first, last = min(r["month"] for r in fact), max(r["month"] for r in fact)
    y, m, out = int(first[:4]), int(first[5:]), []
    while f"{y}-{m:02d}" <= last:
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def util_by_point(points, rows, dates):
    """Per known point: occupied slot-days / available slot-days (None when nothing was available)."""
    occ = defaultdict(float)
    for r in rows:
        if r["point"] != UNKNOWN_ID:
            occ[r["point"]] += r["dwell"]
    res = {}
    for pid, p in points.items():
        avail = p["capacity"] * sum(1 for d in dates if d >= p["opening"])
        res[pid] = (occ[pid] / avail) if avail else None
    return res


def base_kpis(points, rows, dates, region=None):
    n = len(rows)
    collected = sum(r["collected"] for r in rows)
    returned = sum(r["returned"] for r in rows)
    w3 = sum(r["within3"] for r in rows)
    dw = [r["dwell"] for r in rows if r["collected"]]
    in_scope_points = {k: v for k, v in points.items() if region is None or v["region"] == region}
    k = {
        "parcels_arrived": n, "parcels_collected": collected, "parcels_returned": returned,
        "collected_within_3d": w3,
        "pickup_rate": collected / n if n else None,
        "pickup_within_3d_rate": w3 / n if n else None,
        "return_rate": returned / n if n else None,
        "avg_dwell_days": sum(dw) / len(dw) if dw else None,
    }
    if region != UNKNOWN_REGION:
        occ = sum(r["dwell"] for r in rows if r["point"] != UNKNOWN_ID)
        avail = sum(p["capacity"] * sum(1 for d in dates if d >= p["opening"]) for p in in_scope_points.values())
        k["utilisation"] = occ / avail if avail else None
        u = [v for v in util_by_point(in_scope_points, rows, dates).values() if v is not None]
        k["overloaded_points"] = sum(v >= OVERLOAD_THRESHOLD for v in u)
    return k


def target_kpis(targets, months, region, actual):
    sel = [t for t in targets if t["month"] in months and (region is None or t["region"] == region)]
    tp = sum(t["parcels"] for t in sel)
    if not sel or tp == 0:
        return {}
    k = {
        "target_parcels": tp,
        "target_pickup_3d_rate": sum(t["pickup3d"] * t["parcels"] for t in sel) / tp,
        "target_return_rate": sum(t["ret"] * t["parcels"] for t in sel) / tp,
        "parcels_vs_target_pct": (actual["parcels_arrived"] - tp) / tp,
    }
    if actual["pickup_within_3d_rate"] is not None:
        k["pickup_3d_vs_target_pp"] = actual["pickup_within_3d_rate"] - k["target_pickup_3d_rate"]
    return k


UNITS = {
    "pickup_rate": "ratio", "pickup_within_3d_rate": "ratio", "return_rate": "ratio", "utilisation": "ratio",
    "target_pickup_3d_rate": "ratio", "target_return_rate": "ratio", "parcels_vs_target_pct": "ratio",
    "pickup_3d_vs_target_pp": "ratio_diff", "return_rate_vs_target_pp": "ratio_diff", "parcels_yoy_pct": "ratio",
    "avg_dwell_days": "days",
}


def main():
    points, fact, targets, dq, unmatched = load()
    months = all_months(fact)
    window = days_in(months)
    results = []   # (kpi_id, scope, scope_value, value)

    def emit(scope, value, kpis):
        for kpi, v in kpis.items():
            if v is not None:
                results.append((kpi, scope, value, v))

    # Network and regions (whole data window)
    base = base_kpis(points, fact, window)
    emit("Network", "All", {**base, **target_kpis(targets, months, None, base)})
    for region in [*dict.fromkeys(p["region"] for p in points.values()), UNKNOWN_REGION]:
        rows = [r for r in fact if r["region"] == region]
        b = base_kpis(points, rows, window, region)
        emit("Region", region, {**b, **(target_kpis(targets, months, region, b) if region != UNKNOWN_REGION else {})})

    # Months (full month filter) incl. time intelligence
    cnt = defaultdict(int)
    for r in fact:
        cnt[r["month"]] += 1
    for m in MONTH_SCOPES:
        rows = [r for r in fact if r["month"] == m]
        b = base_kpis(points, rows, days_in([m]))
        k = {**b, **target_kpis(targets, [m], None, b)}
        year, mo = int(m[:4]), int(m[5:])
        k["parcels_mtd"] = cnt[m]
        k["parcels_ytd"] = sum(c for mm, c in cnt.items() if mm[:4] == m[:4] and mm <= m)
        py = f"{year - 1}-{mo:02d}"
        if py in cnt:
            k["parcels_py"] = cnt[py]
            k["parcels_yoy_pct"] = (cnt[m] - cnt[py]) / cnt[py]
        r3 = [f"{year - ((mo - i) <= 0)}-{(mo - i - 1) % 12 + 1:02d}" for i in (2, 1, 0)]
        k["parcels_rolling_3m"] = sum(cnt[x] for x in r3)
        emit("Month", m, k)

    emit("DataQuality", "All", dq)

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["kpi_id", "scope", "scope_value", "expected_value", "unit"])
        for kpi, scope, value, v in results:
            w.writerow([kpi, scope, value, f"{v:.9f}".rstrip("0").rstrip(".") if isinstance(v, float) else v,
                        UNITS.get(kpi, "count")])

    print(f"wrote {OUT.relative_to(ROOT)}: {len(results)} rows")
    for key, value in dq.items():
        print(f"  {key:32s} {value}")
    print("  unmatched point ids:", unmatched)


if __name__ == "__main__":
    main()
