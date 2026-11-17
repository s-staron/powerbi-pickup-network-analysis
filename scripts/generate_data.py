#!/usr/bin/env python3
"""Generate the synthetic Norvane Parcel pickup-network data.

Everything is random but seeded: the same seed always produces byte-identical
CSV files.  Nothing here is real data.

The script writes "source-system exports" (data/raw) and two reference tables
(data/reference).  Quality problems are planted on purpose (see step 2 in
main()); the planted counts are printed so they can be compared with what
validation/reconcile.py finds.

Usage:
    python scripts/generate_data.py            # seed 42, writes into ./data
    python scripts/generate_data.py --seed 7
"""
from __future__ import annotations

import argparse
import csv
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_START = date(2024, 7, 1)      # first arrival day in the export
DATA_END = date(2025, 12, 31)      # last arrival day in the export
EXPORT_DATE = date(2026, 1, 15)    # every parcel is resolved by this day

REGIONS = {
    # region: (cities, number of points, share of lockers, volume factor)
    "Central": (["Warszawa", "Łódź", "Radom", "Płock"], 24, 0.55, 1.25),
    "South": (["Kraków", "Katowice", "Rzeszów", "Bielsko-Biała"], 20, 0.45, 1.00),
    "West": (["Poznań", "Wrocław", "Zielona Góra", "Opole"], 18, 0.45, 1.00),
    "North": (["Gdańsk", "Gdynia", "Szczecin", "Olsztyn"], 16, 0.45, 0.95),
    "East": (["Lublin", "Białystok", "Kielce", "Zamość"], 12, 0.30, 0.70),
}

# Spelling variants that the "source system" produced for the city column.
CITY_VARIANTS = {
    "Warszawa": ["Warsaw", "warszawa", "WARSZAWA"],
    "Łódź": ["Lodz", "Łodz", "LODZ", "łódź"],
    "Radom": ["radom"],
    "Płock": ["Plock", "PŁOCK"],
    "Kraków": ["Krakow", "KRAKÓW", "Cracow", "krakow "],
    "Katowice": ["katowice"],
    "Rzeszów": ["Rzeszow", "RZESZÓW"],
    "Bielsko-Biała": ["Bielsko Biala", "Bielsko-Biala"],
    "Poznań": ["Poznan", "POZNAŃ"],
    "Wrocław": ["Wroclaw", "wrocław", "WROCŁAW"],
    "Zielona Góra": ["Zielona Gora", "zielona góra"],
    "Opole": ["opole"],
    "Gdańsk": ["Gdansk", "GDAŃSK", "gdańsk"],
    "Gdynia": ["gdynia"],
    "Szczecin": ["szczecin "],
    "Olsztyn": ["olsztyn"],
    "Lublin": ["lublin"],
    "Białystok": ["Bialystok", "BIAŁYSTOK"],
    "Kielce": ["kielce"],
    "Zamość": ["Zamosc"],
}

LOCKER_PARTNERS = ["Supermarket car park", "Residential estate", "Transport hub", "Petrol station"]
SHOP_PARTNERS = ["Convenience store", "Newsagent", "Pharmacy", "Petrol station"]

SERVICE_TYPES = [("Standard", 0.78), ("Express", 0.12), ("Cash on delivery", 0.10)]
SENDER_SEGMENTS = [("Large e-commerce", 0.45), ("Marketplace seller", 0.25),
                   ("Small online shop", 0.20), ("Private sender", 0.10)]

WEEKDAY_FACTOR = [1.15, 1.25, 1.20, 1.20, 1.10, 0.60, 0.15]  # Mon..Sun, arrivals
ARRIVAL_HOUR_WEIGHTS = [(8, 2), (9, 4), (10, 8), (11, 10), (12, 9), (13, 7),
                        (14, 7), (15, 8), (16, 8), (17, 6), (18, 3), (19, 1)]
MONTH_FACTOR = {1: 0.92, 2: 0.90, 3: 0.95, 4: 0.97, 5: 0.98, 6: 0.95,
                7: 0.90, 8: 0.90, 9: 1.00, 10: 1.05}

DECOMMISSIONED = ("PP-091", "PP-092")   # closed in March 2025, missing from the points export

# Planted-issue rates (step 2 of main)
DUPLICATE_RATE = 0.009
NON_ISO_DATE_RATE = 0.04
CITY_VARIANT_RATE = 0.45
POINT_DATE_DOTTED_RATE = 0.20

ISO = "%Y-%m-%d %H:%M:%S"
DOTTED = "%d.%m.%Y %H:%M:%S"


def weighted(rng: random.Random, pairs):
    total = sum(w for _, w in pairs)
    r = rng.random() * total
    acc = 0.0
    for value, w in pairs:
        acc += w
        if r < acc:
            return value
    return pairs[-1][0]


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def black_friday(year: int) -> date:
    first = date(year, 11, 1)
    thursdays = [first + timedelta(days=i) for i in range(30) if (first + timedelta(days=i)).weekday() == 3]
    return thursdays[3] + timedelta(days=1)  # the day after the 4th Thursday


def seasonal_factor(d: date) -> float:
    growth = 1.0 + 0.08 * (d - DATA_START).days / 365.0
    if d.month <= 10:
        f = MONTH_FACTOR[d.month]
    elif d.month == 11:
        bf = black_friday(d.year)
        f = 1.30
        if d == bf:
            f = 1.90
        elif d == bf + timedelta(days=3):  # Cyber Monday
            f = 1.65
    else:  # December
        if d.day <= 14:
            f = 1.75
        elif d.day <= 22:
            f = 2.05
        elif d.day == 23:
            f = 1.50
        elif d.day <= 26:
            f = 0.30
        else:
            f = 0.90
    return f * growth


def build_points(rng: random.Random):
    """Return all points (dicts), including the 2 decommissioned ones."""
    points = []
    for region, (cities, n, locker_share, vol) in REGIONS.items():
        for i in range(n):
            is_locker = rng.random() < locker_share
            capacity = rng.choice([12, 16, 20, 24, 30, 40]) if is_locker else rng.choice([8, 10, 12, 15, 20])
            base = math.exp(rng.gauss(math.log(2.4 if is_locker else 1.5), 0.45 if is_locker else 0.5))
            span = (date(2024, 6, 30) - date(2018, 1, 1)).days
            points.append({
                "region": region, "city": cities[i % len(cities)],
                "type": "Parcel locker" if is_locker else "Parcel shop",
                "partner": rng.choice(LOCKER_PARTNERS if is_locker else SHOP_PARTNERS),
                "capacity": capacity, "base": base * vol,
                "opening": date(2018, 1, 1) + timedelta(days=rng.randint(0, span)),
                "active_until": None, "role": "normal",
            })
    rng.shuffle(points)
    for idx, p in enumerate(points, start=1):
        p["id"] = f"PP-{idx:03d}"

    # a few overloaded points (high volume, modest capacity) and underused points (low volume)
    lockers = [p for p in points if p["type"] == "Parcel locker" and p["region"] in ("Central", "North", "South")]
    shops = [p for p in points if p["type"] == "Parcel shop" and p["region"] in ("Central", "West")]
    for p in rng.sample(lockers, 4) + rng.sample(shops, 2):
        p["base"] *= 2.4
        p["capacity"] = max(10, min(p["capacity"], 12)) if p["type"] == "Parcel shop" else max(24, p["capacity"])
        p["role"] = "overloaded"
    pool = [p for p in points if p["role"] == "normal" and p["region"] in ("East", "North", "West")]
    for p in rng.sample(pool, 8):
        p["base"] *= 0.30
        p["role"] = "underused"

    # 6 points that opened inside the data window (they ramp up over 90 days)
    for p in rng.sample([x for x in points if x["role"] == "normal"], 6):
        p["opening"] = date(2024, 9, 1) + timedelta(days=rng.randint(0, 300))
        p["role"] = "new"

    # 2 points closed in March 2025; they will be missing from the points export
    for k, region in ((91, "Central"), (92, "South")):
        points.append({
            "id": f"PP-{k:03d}", "region": region, "city": REGIONS[region][0][0], "type": "Parcel shop",
            "partner": "Convenience store", "capacity": 10, "base": 0.8, "opening": date(2020, 1, 1),
            "active_until": date(2025, 3, 31), "role": "decommissioned",
        })
    return points


def arrival_time(rng: random.Random, d: date) -> datetime:
    hour = weighted(rng, ARRIVAL_HOUR_WEIGHTS)
    return datetime(d.year, d.month, d.day, hour, rng.randint(0, 59), rng.randint(0, 59))


def generate_parcels(rng: random.Random, points):
    rows = []
    for p in points:
        is_locker = p["type"] == "Parcel locker"
        d = DATA_START
        while d <= DATA_END:
            if d >= p["opening"] and (p["active_until"] is None or d <= p["active_until"]):
                ramp = 1.0
                days_open = (d - p["opening"]).days
                if p["role"] == "new" and days_open < 90:
                    ramp = 0.3 + 0.7 * days_open / 90.0
                lam = p["base"] * seasonal_factor(d) * WEEKDAY_FACTOR[d.weekday()] * ramp
                for _ in range(poisson(rng, lam)):
                    rows.append(make_parcel(rng, p, d, is_locker))
            d += timedelta(days=1)
    rows.sort(key=lambda r: (r["arrival"], r["point_id"]))
    return rows


def make_parcel(rng: random.Random, p, d: date, is_locker: bool):
    arrival = arrival_time(rng, d)
    service = weighted(rng, SERVICE_TYPES)
    segment = weighted(rng, SENDER_SEGMENTS)
    peak = d.month == 12 and d.day >= 15

    p_return = 0.045
    p_return *= 0.80 if is_locker else 1.15
    p_return *= {"Cash on delivery": 2.0, "Express": 0.6}.get(service, 1.0)
    p_return *= {"Private sender": 1.4, "Marketplace seller": 1.1, "Large e-commerce": 0.85}.get(segment, 1.0)
    p_return *= 1.25 if peak else 1.0
    p_return *= {"West": 1.35, "East": 1.10}.get(p["region"], 1.0)
    if p["role"] == "overloaded":
        p_return += 0.015
    p_return = min(max(p_return, 0.02), 0.30)

    row = {"point_id": p["id"], "arrival": arrival, "pickup": None, "return": None,
           "status": "Collected", "reason": "", "service": service, "segment": segment}

    if rng.random() < p_return:
        full = 0.06 if p["role"] == "overloaded" else 0.0
        reason = weighted(rng, [("Storage period expired", 0.70 - full), ("Refused by recipient", 0.14),
                                ("Point closed or full", 0.06 + full), ("Parcel damaged", 0.05),
                                ("Sender recall", 0.05)])
        if reason == "Storage period expired":
            ret = arrival + timedelta(days=7, hours=rng.randint(24, 48))
        elif reason in ("Parcel damaged", "Sender recall"):
            ret = arrival + timedelta(days=rng.uniform(1, 3))
        else:
            ret = arrival + timedelta(days=rng.uniform(1, 6))
        row["status"], row["reason"], row["return"] = "Returned", reason, ret.replace(microsecond=0)
        return row

    median = 1.0 if is_locker else 1.6
    sigma = 0.85 if is_locker else 0.80
    mult = {"Express": 0.6, "Cash on delivery": 1.2}.get(service, 1.0)
    mult *= 1.15 if peak else 1.0
    mult *= {"West": 1.30, "East": 0.95}.get(p["region"], 1.0)
    delay = min(math.exp(rng.gauss(math.log(median * mult), sigma)), 6.9)
    pickup = arrival + timedelta(days=delay)
    if not is_locker:  # shops: open 08:00-20:00, closed on Sunday
        if pickup.hour < 8:
            pickup = pickup.replace(hour=8, minute=rng.randint(0, 59))
        elif pickup.hour >= 20:
            pickup = (pickup + timedelta(days=1)).replace(hour=8, minute=rng.randint(0, 59))
        if pickup.weekday() == 6:
            pickup += timedelta(days=1)
    row["pickup"] = max(pickup, arrival + timedelta(minutes=10)).replace(microsecond=0)
    return row


def write_csv(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data"))
    args = ap.parse_args()
    out = Path(args.out)
    rng = random.Random(args.seed)

    # ---- step 1: a clean world ---------------------------------------------------
    points = build_points(rng)
    parcels = generate_parcels(rng, points)
    point_region = {p["id"]: p["region"] for p in points}

    # monthly targets per region: a noisy plan around the actual regional volumes
    by_region_month = defaultdict(int)
    for r in parcels:
        if r["point_id"] not in DECOMMISSIONED:
            by_region_month[(point_region[r["point_id"]], r["arrival"].strftime("%Y-%m"))] += 1
    plan_bias = {"Central": 1.02, "South": 1.04, "West": 1.05, "North": 0.99, "East": 1.14}
    months = sorted({m for _, m in by_region_month})
    targets = []
    for region in REGIONS:
        for m in months:
            plan = int(round(by_region_month[(region, m)] * plan_bias[region] * rng.uniform(0.95, 1.05), -1))
            targets.append([region, m + "-01", plan, 0.82, 0.065 if m.endswith("-12") else 0.055])

    # ---- step 2: plant the quality issues ----------------------------------------
    # (a) mixed timestamp formats, (b) returned parcels without a pickup time ('' or 'NULL'),
    # (c) exact duplicate rows from an export that was re-run for overlapping windows
    exported, n_dotted, n_null_text, n_blank, n_dups = [], 0, 0, 0, 0
    parcel_no = 100000000
    for r in parcels:
        dotted = rng.random() < NON_ISO_DATE_RATE
        fmt = DOTTED if dotted else ISO
        n_dotted += dotted
        pickup = r["pickup"].strftime(fmt) if r["pickup"] else ""
        if r["status"] == "Returned":
            pickup = "NULL" if rng.random() < 0.5 else ""
            n_null_text += pickup == "NULL"
            n_blank += pickup == ""
        parcel_no += rng.randint(1, 3)
        row = [f"PX{parcel_no:09d}", r["point_id"], r["arrival"].strftime(fmt), pickup,
               r["return"].strftime(fmt) if r["return"] else "", r["status"], r["reason"],
               r["service"], r["segment"]]
        exported.append(row)
        if rng.random() < DUPLICATE_RATE:
            exported.append(list(row))
            n_dups += 1
    write_csv(out / "raw" / "parcels_export.csv",
              ["parcel_id", "point_id", "arrival_ts", "pickup_ts", "return_ts", "status",
               "return_reason", "service_type", "sender_segment"], exported)

    # (d) points: two closed points are missing, city spelling is inconsistent,
    #     opening_date arrives in two formats
    point_rows, n_city_var, n_dotted_open = [], 0, 0
    for p in sorted(points, key=lambda x: x["id"]):
        if p["id"] in DECOMMISSIONED:
            continue
        city_out = p["city"]
        if rng.random() < CITY_VARIANT_RATE:
            city_out = rng.choice(CITY_VARIANTS[p["city"]])
            n_city_var += city_out != p["city"]
        dotted = rng.random() < POINT_DATE_DOTTED_RATE
        n_dotted_open += dotted
        opening = p["opening"].strftime("%d.%m.%Y") if dotted else p["opening"].isoformat()
        name = f"{p['city']} {p['partner']} {p['id'][3:]}"
        point_rows.append([p["id"], name, p["type"], p["region"], city_out, p["partner"], p["capacity"], opening])
    write_csv(out / "raw" / "pickup_points_export.csv",
              ["point_id", "point_name", "point_type", "region", "city", "partner_category",
               "capacity_slots", "opening_date"], point_rows)

    write_csv(out / "raw" / "monthly_targets_export.csv",
              ["region", "month", "target_parcels", "target_pickup_3d_rate", "target_return_rate"], targets)

    # ---- reference tables (maintained by hand in real life) -----------------------
    ref = set()
    for canon, variants in CITY_VARIANTS.items():
        for v in [canon, *variants]:
            ref.add((v.strip().lower(), canon))
    write_csv(out / "reference" / "city_mapping.csv", ["city_key", "city"], sorted(ref))
    write_csv(out / "reference" / "user_region_mapping.csv", ["user_email", "region"],
              [["central.manager@example.com", "Central"], ["south.manager@example.com", "South"],
               ["west.manager@example.com", "West"], ["north.manager@example.com", "North"],
               ["east.manager@example.com", "East"], ["north.east.manager@example.com", "North"],
               ["north.east.manager@example.com", "East"]])

    print(f"seed={args.seed}")
    print(f"parcels generated before planting issues: {len(parcels)}")
    print(f"rows in parcels_export.csv: {len(exported)}  (exact duplicates planted: {n_dups})")
    print(f"parcel rows with dd.MM.yyyy timestamps: {n_dotted}")
    print(f"returned rows with pickup_ts 'NULL': {n_null_text}, blank: {n_blank}")
    print(f"points exported: {len(point_rows)}; city variants planted: {n_city_var}; "
          f"dotted opening dates: {n_dotted_open}")
    print(f"point ids missing from the points table: {', '.join(DECOMMISSIONED)}")


if __name__ == "__main__":
    main()
