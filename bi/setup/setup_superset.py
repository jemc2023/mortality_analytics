#!/usr/bin/env python3
"""Programmatic creation of all Superset assets for the Mortality Analytics BI layer.

Orchestrates the end-to-end flow:
  1. Authenticate with Superset
  2. Register the Greenplum database connection
  3. Create datasets for each analytical view
  4. Create all 14 charts across 3 dashboards
  5. Place charts onto their dashboards with layout positions

Usage:
    python -m bi.setup.setup_superset

Environment variables (all optional):
    SUPERSET_URL   — Superset base URL (default http://localhost:8088)
    SUPERSET_USER  — Superset admin user (default admin)
    SUPERSET_PASS  — Superset admin password (default admin)
    GREENPLUM_HOST — Greenplum hostname (default dw-greenplum)
"""

import sys

from bi.setup.auth import authenticate
from bi.setup.client import SessionManager
from bi.setup.database import get_or_create_database
from bi.setup.dataset import get_or_create_dataset
from bi.setup.chart import get_or_create_chart
from bi.setup.dashboard import (
    get_or_create_dashboard,
    add_charts_to_dashboard,
)
from bi.setup.config import (
    SUPERSET_URL,
    SUPERSET_USER,
    SUPERSET_PASS,
    DB_NAME,
    DB_URI,
    DATASETS,
    DASHBOARDS,
    dashboard1_charts,
    dashboard2_charts,
    dashboard3_charts,
)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_setup() -> dict:
    """Execute the full asset creation pipeline.

    Returns:
        dict with keys:
            - database_id (int)
            - dataset_ids (dict[str, int])
            - chart_ids (dict[str, int])
            - dashboard_ids (dict[str, int])
    """
    print(f"=== Superset Setup: {SUPERSET_URL} ===")

    # ---- 1. Authenticate ------------------------------------------------
    print("Authenticating ...")
    auth = authenticate(SUPERSET_URL, SUPERSET_USER, SUPERSET_PASS)
    client = SessionManager(SUPERSET_URL, auth["session"])
    print("  ✓ Authenticated")

    # ---- 2. Database connection ----------------------------------------
    print(f"Registering database '{DB_NAME}' ...")
    db_id = get_or_create_database(
        client.session, client.base_url, DB_NAME, DB_URI,
    )
    print(f"  ✓ Database ID: {db_id}")

    # ---- 3. Datasets ---------------------------------------------------
    dataset_ids: dict[str, int] = {}
    for ds in DATASETS:
        print(f"Registering dataset '{ds['name']}' "
              f"({ds['schema']}.{ds['table']}) ...")
        ds_id = get_or_create_dataset(
            client.session, client.base_url,
            db_id, ds["schema"], ds["table"],
        )
        dataset_ids[ds["name"]] = ds_id
        print(f"  ✓ Dataset ID: {ds_id}")

    # Short aliases for readability
    ine_id = dataset_ids["INE - Mortalidad Completa"]
    mspas_id = dataset_ids["MSPAS - Mortalidad Nacional"]
    ihme_id = dataset_ids["IHME - Carga Enfermedad CA"]

    # ---- 4. Dashboards & charts ----------------------------------------
    chart_ids: dict[str, int] = {}
    dashboard_ids: dict[str, int] = {}

    # Dashboard 1: Pre vs Post COVID
    _build_dashboard(
        client, DASHBOARDS[0],
        dashboard1_charts(ine_id, mspas_id),
        chart_ids, dashboard_ids,
    )

    # Dashboard 2: Causas de Muerte
    _build_dashboard(
        client, DASHBOARDS[1],
        dashboard2_charts(ine_id, ihme_id),
        chart_ids, dashboard_ids,
    )

    # Dashboard 3: Geografia y Demografia
    _build_dashboard(
        client, DASHBOARDS[2],
        dashboard3_charts(ine_id),
        chart_ids, dashboard_ids,
    )

    print("\n=== Setup Complete ===")
    print(f"Database:  {db_id}")
    for name, dsid in dataset_ids.items():
        print(f"Dataset:   {name} → {dsid}")
    for name, cid in chart_ids.items():
        print(f"Chart:     {name} → {cid}")
    for name, did in dashboard_ids.items():
        print(f"Dashboard: {name} → {did}")

    return {
        "database_id": db_id,
        "dataset_ids": dataset_ids,
        "chart_ids": chart_ids,
        "dashboard_ids": dashboard_ids,
    }


def _build_dashboard(
    client: SessionManager,
    title: str,
    charts: list[dict],
    chart_registry: dict[str, int],
    dashboard_registry: dict[str, int],
) -> None:
    """Create a dashboard, its charts, and place them.

    Args:
        client: Authenticated SessionManager.
        title: Dashboard display title.
        charts: List of chart config dicts.
        chart_registry: Mutable dict to register created chart IDs.
        dashboard_registry: Mutable dict to register created dashboard IDs.
    """
    print(f"\n--- Dashboard: {title} ---")

    # Create / retrieve dashboard
    dash_id = get_or_create_dashboard(client.session, client.base_url, title)
    dashboard_registry[title] = dash_id
    print(f"  Dashboard ID: {dash_id}")

    # Create / retrieve each chart
    positions = []
    for chart_cfg in charts:
        slice_name = chart_cfg["slice_name"]
        cid = get_or_create_chart(client.session, client.base_url, chart_cfg)
        chart_registry[slice_name] = cid
        positions.append({
            "chart_id": cid,
            "width": 12,
            "height": 50,
        })
        print(f"  ✓ Chart: {slice_name} → {cid}")

    # Place charts on dashboard
    add_charts_to_dashboard(
        client.session, client.base_url, dash_id, positions,
    )
    print(f"  ✓ Charts placed on dashboard")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        run_setup()
    except Exception as exc:
        print(f"\n✗ Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)
