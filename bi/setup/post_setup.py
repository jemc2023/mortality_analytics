#!/usr/bin/env python3
"""Post-setup fixes for Apache Superset v5+.

Applies corrections after ``make setup`` that the REST API alone cannot handle:
  1. Converts string metrics (e.g. "SUM(defuncion)") to SIMPLE format with unique labels
  2. Adds ``time_range: "No filter"`` to all charts to prevent "Datetime column" errors
  3. Sets correct position_json for each dashboard with proper chart assignments
  4. Saves SUM/AVG metrics on each dataset so charts can reference them

Usage:
    cd .. && PYTHONPATH=. python3 -m bi.setup.post_setup

Environment:
    SUPERSET_URL  — Superset base URL (default http://localhost:8088)
    SUPERSET_USER — Superset admin user (default admin)
    SUPERSET_PASS — Superset admin password (default admin)
"""

import os
import json
import re
import time
import uuid
import requests

from bi.setup.config import DASHBOARDS, DATASETS

BASE = os.environ.get("SUPERSET_URL", "http://localhost:8088")
USER = os.environ.get("SUPERSET_USER", "admin")
PASS = os.environ.get("SUPERSET_PASS", "admin")

session = requests.Session()
r = session.post(f"{BASE}/api/v1/security/login", json={"username": USER, "password": PASS, "provider": "db"})
r.raise_for_status()
session.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
r = session.get(f"{BASE}/api/v1/security/csrf_token/")
r.raise_for_status()
session.headers.update({"X-CSRFToken": r.json()["result"], "Referer": BASE})


def fix_chart_metrics(chart_id: int) -> bool:
    """Fix chart params: convert string metrics to SIMPLE format, add time_range."""
    r = session.get(f"{BASE}/api/v1/chart/{chart_id}")
    if r.status_code != 200:
        return False
    c = r.json()["result"]
    params = json.loads(c.get("params") or "{}")
    qc_raw = c.get("query_context")
    qc = json.loads(qc_raw) if qc_raw else {}

    changed = False
    for key in ["metrics", "groupby"]:
        if key in params and isinstance(params[key], list):
            new_list = []
            for m in params[key]:
                if isinstance(m, str):
                    match = re.match(r"(SUM|AVG|COUNT|MAX|MIN)\((\w+)\)", m)
                    if match:
                        agg, col = match.group(1), match.group(2)
                        new_list.append({"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": agg, "label": m})
                        changed = True
                    else:
                        new_list.append(m)
                else:
                    new_list.append(m)
            params[key] = new_list

    if isinstance(params.get("metric"), str):
        match = re.match(r"(SUM|AVG|COUNT|MAX|MIN)\((\w+)\)", params["metric"])
        if match:
            agg, col = match.group(1), match.group(2)
            params["metric"] = {
                "expressionType": "SIMPLE",
                "column": {"column_name": col},
                "aggregate": agg,
                "label": params["metric"],
            }
            changed = True

    if "time_range" not in params:
        params["time_range"] = "No filter"
        changed = True

    if qc.get("queries"):
        for key in ["metrics", "columns"]:
            if key in qc["queries"][0] and isinstance(qc["queries"][0][key], list):
                new_list = []
                for m in qc["queries"][0][key]:
                    if isinstance(m, str):
                        match = re.match(r"(SUM|AVG|COUNT|MAX|MIN)\((\w+)\)", m)
                        if match:
                            agg, col = match.group(1), match.group(2)
                            new_list.append({"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": agg, "label": m})
                            changed = True
                        else:
                            new_list.append(m)
                    else:
                        new_list.append(m)
                qc["queries"][0][key] = new_list
        if "time_range" not in qc["queries"][0]:
            qc["queries"][0]["time_range"] = "No filter"
            changed = True

    if changed:
        payload = {"params": json.dumps(params), "query_context": json.dumps(qc), "query_context_generation": False}
        r = session.put(f"{BASE}/api/v1/chart/{chart_id}", json=payload)
        return r.status_code == 200
    return True


def add_dataset_metrics(dataset_id: int, col_name: str, agg: str) -> bool:
    """Add a saved metric to a dataset if it doesn't exist."""
    r = session.get(f"{BASE}/api/v1/dataset/{dataset_id}")
    if r.status_code != 200:
        return False
    existing = [m["metric_name"] for m in r.json()["result"].get("metrics", [])]
    metric_name = f"{agg}({col_name})"
    if metric_name in existing:
        return True
    payload = {"metrics": [{"metric_name": metric_name, "expression": metric_name, "metric_type": agg.lower(), "verbose_name": metric_name}]}
    r = session.put(f"{BASE}/api/v1/dataset/{dataset_id}", json=payload)
    return r.status_code == 200


def fix_dashboard_layout(dashboard_id: int, rows: list[list[dict]]) -> bool:
    """Set a compact multi-column dashboard position_json."""
    chart_uuids = {}
    for row in rows:
        for chart in row:
            cid = chart["chart_id"]
            r = session.get(f"{BASE}/api/v1/chart/{cid}")
            if r.status_code == 200:
                chart_uuids[cid] = r.json()["result"]["uuid"]

    root, grid = "ROOT_ID", "GRID_ID"
    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        root: {"id": root, "type": "ROOT", "children": [grid]},
        grid: {"id": grid, "type": "GRID", "children": []},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": "Overview"}},
    }
    for row in rows:
        rid = f"ROW-{str(uuid.uuid4())[:8]}"
        pos[grid]["children"].append(rid)
        pos[rid] = {"id": rid, "type": "ROW", "children": [], "meta": {"background": "BACKGROUND_TRANSPARENT"}, "parents": [root, grid]}
        for chart in row:
            cid = chart["chart_id"]
            cn = f"CHART-{str(uuid.uuid4())[:8]}"
            pos[rid]["children"].append(cn)
            pos[cn] = {
                "id": cn,
                "type": "CHART",
                "children": [],
                "meta": {
                    "chartId": cid,
                    "height": chart.get("height", 50),
                    "width": chart.get("width", 6),
                    "uuid": chart_uuids.get(cid, ""),
                },
                "parents": [root, grid, rid],
            }

    r = session.put(f"{BASE}/api/v1/dashboard/{dashboard_id}", json={"position_json": json.dumps(pos)})
    if r.status_code != 200:
        print(f"    layout error {dashboard_id}: {r.status_code} {r.text[:500]}")
    return r.status_code == 200


def list_all(endpoint: str, page_size: int = 100) -> list[dict]:
    """Return all rows from a simple Superset REST list endpoint."""
    rows: list[dict] = []
    page = 0
    while True:
        r = session.get(
            f"{BASE}/api/v1/{endpoint}/",
            params={"page": page, "page_size": page_size},
        )
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("result", [])
        rows.extend(batch)
        total = payload.get("count")
        if len(batch) < page_size or (isinstance(total, int) and len(rows) >= total):
            return rows
        page += 1


def chart_id_by_name(name: str, charts: list[dict]) -> int | None:
    """Find a chart ID by slice name."""
    for chart in charts:
        if chart.get("slice_name") == name:
            return chart.get("id")
    return None


def dashboard_id_by_title(title: str, dashboards: list[dict]) -> int | None:
    """Find a dashboard ID by title."""
    for dashboard in dashboards:
        if dashboard.get("dashboard_title") == title:
            return dashboard.get("id")
    return None


def chart_ref(name: str, width: int, height: int, charts: list[dict]) -> dict:
    """Build a layout chart reference from its slice name."""
    cid = chart_id_by_name(name, charts)
    if cid is None:
        raise RuntimeError(f"Chart not found: {name}")
    return {"chart_id": cid, "width": width, "height": height}


def dataset_id_by_table(schema: str, table_name: str, datasets: list[dict]) -> int | None:
    """Find a dataset ID by schema-qualified table name."""
    for dataset in datasets:
        if dataset.get("schema") == schema and dataset.get("table_name") == table_name:
            return dataset.get("id")
    return None


def main():
    print("=== Post-setup fixes ===")

    charts = list_all("chart")
    dashboards = list_all("dashboard")
    datasets = list_all("dataset")

    # 1. Fix all charts
    for item in charts:
        cid = item["id"]
        ok = fix_chart_metrics(cid)
        print(f"  Chart {cid}: {'✓' if ok else '✗'}")

    # 2. Add saved metrics
    metric_specs = {
        "v_ine_completa": ("defuncion", "SUM"),
        "v_mspas_nacional": ("tasa_por_100k", "AVG"),
        "v_ihme_centroamerica": ("valor", "SUM"),
    }
    for dataset_cfg in DATASETS:
        table = dataset_cfg["table"]
        if table not in metric_specs:
            continue
        col, agg = metric_specs[table]
        ds_id = dataset_id_by_table(dataset_cfg["schema"], table, datasets)
        if ds_id is None:
            print(f"  Dataset {dataset_cfg['schema']}.{table} {agg}({col}): ✗ not found")
            continue
        ok = add_dataset_metrics(ds_id, col, agg)
        print(f"  Dataset {ds_id} {agg}({col}): {'✓' if ok else '✗'}")

    # 3. Fix dashboard layouts
    layouts = {
        DASHBOARDS[0]: [
            [
                chart_ref("Total Defunciones Pre-COVID (2015-2019)", 4, 24, charts),
                chart_ref("Total Defunciones Post-COVID (2020-2024)", 4, 24, charts),
                chart_ref("Variacion Pre vs Post COVID", 4, 24, charts),
            ],
            [chart_ref("Defunciones Mensuales 2015-2024", 12, 58, charts)],
            [
                chart_ref("Defunciones por Ano — Pre vs Post COVID", 6, 44, charts),
                chart_ref("Tasa de Mortalidad Nacional x 100k hab (MSPAS)", 6, 44, charts),
            ],
        ],
        DASHBOARDS[1]: [
            [chart_ref("Defunciones por Causa GBD L2", 12, 55, charts)],
            [
                chart_ref("Top 10 Causas de Muerte", 6, 48, charts),
                chart_ref("Tendencia Pre vs Post COVID", 6, 48, charts),
            ],
            [chart_ref("Tendencia de Causas en Centroamerica (IHME)", 12, 50, charts)],
        ],
        DASHBOARDS[2]: [
            [
                chart_ref("Defunciones por Departamento", 6, 55, charts),
                chart_ref("Defunciones por Grupo Etario y Ano", 6, 55, charts),
            ],
            [
                chart_ref("Defunciones por Sexo y Año", 6, 48, charts),
                chart_ref("Resumen: Departamento x Causa", 6, 48, charts),
            ],
        ],
    }
    for title, rows in layouts.items():
        time.sleep(0.5)
        dash_id = dashboard_id_by_title(title, dashboards)
        if dash_id is None:
            print(f"  Dashboard {title}: ✗ not found")
            continue
        ok = fix_dashboard_layout(dash_id, rows)
        print(f"  Dashboard {dash_id}: {'✓' if ok else '✗'}")

    print("=== Done ===")
    print("Next: drag charts into dashboards via UI, or use export/import for automatic association.")


if __name__ == "__main__":
    main()
