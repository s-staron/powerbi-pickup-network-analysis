#!/usr/bin/env python3
"""Second, independent check of expected_results.csv, written in SQL (SQLite).

reconcile.py computes the expected values in Python.  This script loads the same raw CSV
files into an in-memory SQLite database, applies the cleaning rules R1-R6 in SQL, computes
the base KPIs again and compares them with validation/expected_results.csv.  If two different
implementations (Python and SQL) agree, a mistake in the expected values is unlikely.

Covered: counts, pickup and return rates, average dwell time, utilisation, and the
data-quality row counts, for the network, every region and two months.
Not covered: targets, time intelligence (MTD, YTD, PY, YoY, rolling 3 months), and top/bottom N.

Run:  python validation/sql_crosscheck.py
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
EXPECTED = Path(__file__).resolve().parent / "expected_results.csv"

DATE_START, DATE_END = "2024-07-01", "2025-12-31"

# ISO form of a timestamp or date that may be written as dd.MM.yyyy[ HH:mm:ss]
def iso(col: str) -> str:
    return (f"CASE WHEN {col} IS NULL OR {col} IN ('', 'NULL') THEN NULL "
            f"WHEN instr({col}, '.') > 0 THEN substr({col}, 7, 4) || '-' || substr({col}, 4, 2) || '-' || substr({col}, 1, 2) || substr({col}, 11) "
            f"ELSE {col} END")


def load(con: sqlite3.Connection, table: str, path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    head, body = rows[0], rows[1:]
    con.execute(f"CREATE TABLE {table} ({', '.join(h + ' TEXT' for h in head)})")
    con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(head))})", body)


def main() -> int:
    con = sqlite3.connect(":memory:")
    load(con, "raw", RAW / "parcels_export.csv")
    load(con, "pts", RAW / "pickup_points_export.csv")
    con.executescript(f"""
        CREATE TABLE dedup AS SELECT DISTINCT * FROM raw;                                   -- R1
        CREATE VIEW points AS SELECT point_id, region, CAST(capacity_slots AS INTEGER) AS cap,
               substr({iso('opening_date')}, 1, 10) AS opened FROM pts;                    -- R6
        CREATE VIEW parcel AS
          SELECT d.status,
                 COALESCE(p.region, 'Unassigned') AS region,                               -- R4
                 CASE WHEN p.point_id IS NULL THEN 0 ELSE 1 END AS known,
                 substr(a, 1, 7) AS month,
                 CAST(strftime('%s', CASE WHEN d.status = 'Collected' THEN k ELSE r END) AS INTEGER)
                   - CAST(strftime('%s', a) AS INTEGER) AS dwell_sec,
                 d.point_id
          FROM (SELECT *, {iso('arrival_ts')} AS a, {iso('pickup_ts')} AS k, {iso('return_ts')} AS r   -- R2, R3
                FROM dedup) d
          LEFT JOIN points p ON p.point_id = d.point_id;
    """)

    def scope_kpis(region=None, month=None):
        where, args = [], []
        if region:
            where.append("region = ?"); args.append(region)
        if month:
            where.append("month = ?"); args.append(month)
        w = ("WHERE " + " AND ".join(where)) if where else ""
        n, coll, ret, w3, dw = con.execute(
            f"""SELECT COUNT(*), SUM(status = 'Collected'), SUM(status = 'Returned'),
                       SUM(status = 'Collected' AND dwell_sec <= 259200),
                       AVG(CASE WHEN status = 'Collected' THEN dwell_sec / 86400.0 END)
                FROM parcel {w}""", args).fetchone()
        k = {"parcels_arrived": n, "parcels_collected": coll, "parcels_returned": ret, "collected_within_3d": w3,
             "pickup_rate": coll / n, "pickup_within_3d_rate": w3 / n, "return_rate": ret / n, "avg_dwell_days": dw}
        if region != "Unassigned":
            start = f"{month}-01" if month else DATE_START
            end = con.execute("SELECT date(?, '+1 month', '-1 day')", (start,)).fetchone()[0] if month else DATE_END
            occ = con.execute(f"SELECT SUM(dwell_sec) / 86400.0 FROM parcel {w + (' AND ' if w else 'WHERE ')}known = 1",
                              args).fetchone()[0]
            preg = "WHERE region = ?" if region else ""
            avail = con.execute(
                f"""SELECT SUM(cap * MAX(0, CAST(julianday(?) - julianday(CASE WHEN opened > ? THEN opened ELSE ? END) + 1 AS INTEGER)))
                    FROM points {preg}""", [end, start, start] + ([region] if region else [])).fetchone()[0]
            k["utilisation"] = occ / avail
        return k

    got = {}
    for kpi, v in scope_kpis().items():
        got[(kpi, "Network", "All")] = v
    for (region,) in con.execute("SELECT DISTINCT region FROM parcel").fetchall():
        for kpi, v in scope_kpis(region=region).items():
            got[(kpi, "Region", region)] = v
    for month in ("2025-09", "2025-12"):
        for kpi, v in scope_kpis(month=month).items():
            got[(kpi, "Month", month)] = v
    raw_rows = con.execute("SELECT COUNT(*) FROM raw").fetchone()[0]
    deduped = con.execute("SELECT COUNT(*) FROM dedup").fetchone()[0]
    got[("dq_raw_rows", "DataQuality", "All")] = raw_rows
    got[("dq_duplicates_removed", "DataQuality", "All")] = raw_rows - deduped
    got[("dq_rows_after_dedupe", "DataQuality", "All")] = deduped
    got[("dq_unmatched_point_rows", "DataQuality", "All")] = con.execute("SELECT COUNT(*) FROM parcel WHERE known = 0").fetchone()[0]
    got[("dq_non_iso_timestamp_rows", "DataQuality", "All")] = con.execute("SELECT COUNT(*) FROM dedup WHERE instr(arrival_ts, '.') > 0").fetchone()[0]
    got[("dq_returned_without_pickup", "DataQuality", "All")] = con.execute(
        "SELECT COUNT(*) FROM dedup WHERE status = 'Returned' AND (pickup_ts IS NULL OR pickup_ts IN ('', 'NULL'))").fetchone()[0]

    expected = {(r["kpi_id"], r["scope"], r["scope_value"]): float(r["expected_value"])
                for r in csv.DictReader(EXPECTED.open(encoding="utf-8"))}
    compared = bad = 0
    for key, value in got.items():
        if key not in expected:
            continue
        compared += 1
        if abs(value - expected[key]) > 1e-6 * max(1.0, abs(expected[key])):
            bad += 1
            print(f"DIFFERENT {key}: sql={value} expected={expected[key]}")
    print(f"compared {compared} expected values with the SQL result; differences: {bad}")
    return 1 if bad or compared == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
