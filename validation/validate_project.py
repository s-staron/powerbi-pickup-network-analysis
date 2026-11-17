#!/usr/bin/env python3
"""Static validation of the Power BI project (no Power BI Desktop needed).

What it checks
  1. Every JSON file that declares a "$schema" is valid against Microsoft's published
     JSON schema (github.com/microsoft/json-schemas). Schemas are downloaded once into
     validation/.schema_cache/.  Needs:  pip install jsonschema referencing
  2. The TMDL files of the semantic model: structure, descriptions, format strings, unique
     lineage tags, relationships, hidden keys, sort-by columns, DAX references, measure count,
     RLS role, and that every KPI of expected_results.csv is covered by the reconciliation measure.
  3. The PBIR report: every field a visual uses exists in the model, every visual has alt text,
     pages listed in pages.json exist, drill-through and tooltip pages are wired.

What it does NOT check: it does not run Power Query or DAX.  Numbers are checked separately
(validation/reconcile.py and the live reconciliation page).

Run:  python validation/validate_project.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "PickupNetwork.SemanticModel"
REPORT = ROOT / "PickupNetwork.Report"
CACHE = Path(__file__).resolve().parent / ".schema_cache"
BASE_URL = "https://developer.microsoft.com/json-schemas/"
RAW_URL = "https://raw.githubusercontent.com/microsoft/json-schemas/main/"

problems: list[str] = []
passed: list[str] = []


def check(ok: bool, name: str, detail: str = ""):
    (passed if ok else problems).append(name if ok else f"{name}: {detail}")


# ---------------------------------------------------------------- 1. JSON schemas
def fetch_schema(url: str):
    rel = url.removeprefix(BASE_URL).split("#")[0]
    local = CACHE / rel
    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(RAW_URL + rel, timeout=30) as r:
            local.write_bytes(r.read())
    return json.loads(local.read_text(encoding="utf-8"))


def validate_json_files():
    try:
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7
    except ImportError:
        problems.append("jsonschema/referencing not installed (pip install jsonschema referencing)")
        return

    def retrieve(uri):
        return Resource.from_contents(fetch_schema(uri), default_specification=DRAFT7)

    registry = Registry(retrieve=retrieve)
    files = [*ROOT.glob("*.pbip"), *MODEL.rglob("*.json"), *MODEL.rglob("*.pbism"), *MODEL.rglob(".platform"),
             *REPORT.rglob("*.json"), *REPORT.rglob("*.pbir"), *REPORT.rglob(".platform")]
    n = 0
    for f in sorted(files):
        if "StaticResources" in f.parts or ".pbi" in f.parts:
            continue
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            problems.append(f"{f.relative_to(ROOT)}: not valid JSON ({e})")
            continue
        n += 1
        url = doc.get("$schema") if isinstance(doc, dict) else None
        if not url:
            continue
        try:
            schema = fetch_schema(url)
            errs = sorted(Draft7Validator(schema, registry=registry).iter_errors(doc), key=lambda e: list(e.path))
        except Exception as e:  # noqa: BLE001
            problems.append(f"{f.relative_to(ROOT)}: schema {url} could not be applied ({e})")
            continue
        for e in errs[:5]:
            problems.append(f"{f.relative_to(ROOT)}: schema error at {'/'.join(map(str, e.path))}: {e.message[:160]}")
        if not errs:
            passed.append(f"schema OK: {f.relative_to(ROOT)}")
    check(n > 0, "JSON files found")


# ---------------------------------------------------------------- 2. TMDL
def unq(name: str) -> str:
    name = name.strip()
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def parse_tmdl():
    """Return tables {name: {...}}, expressions, relationships, roles; collects structural problems."""
    tables, expressions, rels, roles = {}, {}, [], {}
    lineage = {}
    for f in sorted((MODEL / "definition").rglob("*.tmdl")):
        lines = f.read_text(encoding="utf-8").split("\n")
        rel = f.relative_to(ROOT)
        for i, line in enumerate(lines, 1):
            if line.startswith(" "):
                problems.append(f"{rel}:{i}: line starts with a space, TMDL uses tabs")
            m = re.match(r"\s*lineageTag: (\S+)", line)
            if m:
                if m.group(1) in lineage:
                    problems.append(f"{rel}:{i}: duplicate lineageTag {m.group(1)} (also {lineage[m.group(1)]})")
                lineage[m.group(1)] = f"{rel}:{i}"
        if f.parent.name == "tables":
            tables[unq(re.match(r"table (.+)", next(l for l in lines if l.startswith("table "))).group(1))] = parse_table(lines, rel)
        elif f.name == "expressions.tmdl":
            parse_expressions(lines, expressions)
        elif f.name == "relationships.tmdl":
            parse_relationships(lines, rels)
        elif f.parent.name == "roles":
            roles[f.stem] = "\n".join(lines)
    return tables, expressions, rels, roles


def parse_table(lines, rel):
    t = {"doc": False, "columns": {}, "measures": {}, "hidden": False, "dataCategory": None, "partition": False}
    prev_doc = False
    cur = None
    for line in lines:
        if line.startswith("///"):
            prev_doc = True
            continue
        if line.startswith("table "):
            t["doc"] = prev_doc
        m = re.match(r"\tcolumn (.+)", line)
        if m:
            cur = ("column", unq(m.group(1)))
            t["columns"][cur[1]] = {"doc": prev_doc, "hidden": False, "key": False, "sortBy": None}
        m = re.match(r"\tmeasure (.+?) =(.*)$", line)
        if m:
            cur = ("measure", unq(m.group(1)))
            t["measures"][cur[1]] = {"doc": prev_doc, "format": False, "folder": False, "expr": m.group(2).strip()}
        if re.match(r"\tpartition ", line):
            cur = ("partition", "")
            t["partition"] = True
        if line.startswith("\t") and not line.startswith("\t\t"):
            if not re.match(r"\t(column|measure|partition|annotation|isHidden|dataCategory|lineageTag|/{3})", line.lstrip("\n")) \
               and line.strip() and not line.startswith("\t///"):
                pass
            if line.strip() == "isHidden":
                t["hidden"] = True
            m2 = re.match(r"\tdataCategory: (\w+)", line)
            if m2:
                t["dataCategory"] = m2.group(1)
        if line.startswith("\t\t") and not line.startswith("\t\t\t") and cur:
            kind, name = cur
            s = line.strip()
            if kind == "column":
                c = t["columns"][name]
                c["hidden"] |= s == "isHidden"
                c["key"] |= s == "isKey"
                if s.startswith("sortByColumn:"):
                    c["sortBy"] = unq(s.split(":", 1)[1])
            elif kind == "measure":
                ms = t["measures"][name]
                ms["format"] |= s.startswith("formatString:")
                ms["folder"] |= s.startswith("displayFolder:")
        if line.startswith("\t\t\t") and cur and cur[0] == "measure":
            t["measures"][cur[1]]["expr"] += " " + line.strip()
        if line.strip() and not line.startswith("///") and not line.startswith("\t///"):
            if not line.startswith("\t\t"):
                prev_doc = False
        if line.startswith("\t///"):
            prev_doc = True
    return t


def parse_expressions(lines, out):
    for line in lines:
        m = re.match(r"expression (.+?) =", line)
        if m:
            out[unq(m.group(1))] = True


def parse_relationships(lines, out):
    cur = {}
    for line in lines:
        if line.startswith("relationship "):
            cur = {"name": line.split(" ", 1)[1].strip()}
            out.append(cur)
        m = re.match(r"\t(fromColumn|toColumn): (.+)", line)
        if m:
            t, c = m.group(2).split(".", 1) if not m.group(2).startswith("'") else (None, None)
            if t is None:
                mm = re.match(r"('.+?'|\S+?)\.(.+)", m.group(2))
                t, c = mm.group(1), mm.group(2)
            cur[m.group(1)] = (unq(t), unq(c))
        if re.match(r"\t(crossFilteringBehavior|isActive|toCardinality|fromCardinality)", line):
            cur["nonDefault"] = line.strip()


TEXT_MEASURES = {"Title Overview", "Title Point Detail", "Utilisation Color", "Check Status"}


def validate_model():
    tables, expressions, rels, roles = parse_tmdl()
    model_text = (MODEL / "definition" / "model.tmdl").read_text(encoding="utf-8")

    refs = re.findall(r"^ref table (.+)$", model_text, re.M)
    check({unq(r) for r in refs} == set(tables), "model.tmdl lists exactly the table files",
          f"{sorted({unq(r) for r in refs} ^ set(tables))}")
    for e in re.findall(r"^ref expression (.+)$", model_text, re.M):
        check(unq(e) in expressions, f"expression {unq(e)} defined")
    check("discourageImplicitMeasures" in model_text, "implicit measures discouraged")
    check("__PBI_TimeIntelligenceEnabled = 0" in model_text, "auto date/time disabled")

    all_measures = {}
    for tn, t in tables.items():
        check(t["doc"], f"table {tn} has a description", "missing /// description")
        check(t["partition"], f"table {tn} has a partition", "no partition")
        for mn, m in t["measures"].items():
            all_measures[mn] = tn
            check(m["doc"], f"measure {mn} has a description", "missing /// description")
            check(m["folder"], f"measure {mn} has a display folder", "missing displayFolder")
            if mn not in TEXT_MEASURES:
                check(m["format"], f"measure {mn} has a format string", "missing formatString")
        for cn, c in t["columns"].items():
            if c["sortBy"]:
                check(c["sortBy"] in t["columns"], f"{tn}[{cn}] sort-by column exists", c["sortBy"])
    n_measures = len(all_measures)
    check(20 <= n_measures <= 30, f"measure count is 20-30 (found {n_measures})", str(n_measures))

    # relationships
    check(len(rels) >= 5, "star schema relationships present")
    for r in rels:
        check("nonDefault" not in r, f"relationship {r['name'][:8]} is many-to-one, single direction, active",
              r.get("nonDefault", ""))
        for side in ("fromColumn", "toColumn"):
            t, c = r[side]
            check(t in tables and c in tables[t]["columns"], f"relationship column {t}[{c}] exists")
            if t in tables and c in tables[t]["columns"]:
                hidden = tables[t]["columns"][c]["hidden"]
                if (t, c) == ("DimDate", "Date"):
                    check(tables[t]["columns"][c]["key"], "DimDate[Date] is the key column")
                else:
                    check(hidden, f"key column {t}[{c}] is hidden", "not hidden")
    dd = tables.get("DimDate", {})
    check(dd.get("dataCategory") == "Time", "DimDate is marked as date table (dataCategory: Time)")

    # DAX references
    names = {(tn, cn) for tn, t in tables.items() for cn in t["columns"]}
    for tn, t in tables.items():
        for mn, m in t["measures"].items():
            expr = m["expr"]
            for tbl, col in re.findall(r"('[^']+'|[A-Za-z_][\w]*)\[([^\]]+)\]", expr):
                tbl = unq(tbl)
                ok = (tbl, col) in names or col in all_measures
                check(ok, f"{mn}: reference {tbl}[{col}] resolves", "unknown column")
            for ref in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", expr):
                check(ref in all_measures, f"{mn}: measure [{ref}] exists", "unknown measure")

    # RLS
    check("Regional Manager" in roles, "RLS role 'Regional Manager' exists")
    if roles:
        role = roles["Regional Manager"]
        check("USERPRINCIPALNAME()" in role and "tablePermission DimRegion" in role, "RLS filters DimRegion by user")

    # reconciliation coverage
    exp = ROOT / "validation" / "expected_results.csv"
    if exp.exists() and "Check Actual" in all_measures:
        expr = tables["_Measures"]["measures"]["Check Actual"]["expr"]
        kpis = {r["kpi_id"] for r in csv.DictReader(exp.open(encoding="utf-8"))
                if r["scope"] != "DataQuality"}
        for k in sorted(kpis):
            check(f'"{k}"' in expr, f"Check Actual covers kpi {k}", "kpi missing from SWITCH")
    return tables, all_measures


# ---------------------------------------------------------------- 3. PBIR
def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def validate_report(tables, all_measures):
    defn = REPORT / "definition"
    pages_meta = json.loads((defn / "pages" / "pages.json").read_text(encoding="utf-8"))
    page_dirs = {p.name for p in (defn / "pages").iterdir() if p.is_dir()}
    check(set(pages_meta["pageOrder"]) == page_dirs, "pages.json lists every page folder",
          str(set(pages_meta["pageOrder"]) ^ page_dirs))
    check(pages_meta.get("activePageName") in page_dirs, "active page exists")
    visible = 0
    n_visuals = 0
    for pd in sorted(page_dirs):
        page = json.loads((defn / "pages" / pd / "page.json").read_text(encoding="utf-8"))
        visible += page.get("visibility") != "HiddenInViewMode" and page.get("type") != "Tooltip"
        if page.get("type") in ("Drillthrough", "Tooltip"):
            bound = {f["name"] for f in page.get("filterConfig", {}).get("filters", [])}
            for prm in page["pageBinding"]["parameters"]:
                check(prm["boundFilter"] in bound, f"{pd}: binding parameter {prm['name']} has its filter")
        for vf in sorted((defn / "pages" / pd / "visuals").glob("*/visual.json")):
            v = json.loads(vf.read_text(encoding="utf-8"))
            n_visuals += 1
            check(v["name"] == vf.parent.name, f"{pd}/{vf.parent.name}: folder equals visual name")
            alt = v["visual"].get("visualContainerObjects", {}).get("general", [{}])[0].get("properties", {}).get("altText")
            check(bool(alt), f"{pd}/{v['name']} has alt text", "missing altText")
            check("tabOrder" in v["position"], f"{pd}/{v['name']} has a tab order")
            for node in walk(v):
                for kind in ("Column", "Measure"):
                    if kind in node and isinstance(node[kind], dict) and "Property" in node[kind]:
                        ent = node[kind]["Expression"]["SourceRef"]["Entity"]
                        prop = node[kind]["Property"]
                        ok = (prop in tables.get(ent, {}).get("columns", {})) if kind == "Column" \
                            else (all_measures.get(prop) == ent)
                        check(ok, f"{pd}/{v['name']}: {kind.lower()} {ent}[{prop}] exists in the model", "unknown field")
            tip = v["visual"].get("visualContainerObjects", {}).get("visualTooltip")
            if tip:
                sec = tip[0]["properties"]["section"]["expr"]["Literal"]["Value"].strip("'")
                check(sec in page_dirs, f"{pd}/{v['name']}: tooltip page {sec} exists")
    check(visible == 4, f"report has 4 visible pages (found {visible})", str(visible))
    theme = REPORT / "StaticResources" / "RegisteredResources" / "PickupNetworkTheme.json"
    check(theme.exists(), "single theme file present")


def main():
    validate_json_files()
    tables, measures = validate_model()
    validate_report(tables, measures)
    print(f"passed checks : {len(passed)}")
    print(f"failed checks : {len(problems)}")
    for p in problems:
        print("  FAIL", p)
    if "-v" in sys.argv:
        for p in passed:
            print("  ok  ", p)
    print(f"measures: {len(measures)}; tables: {', '.join(tables)}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
