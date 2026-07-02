#!/usr/bin/env python3
"""Export Superset dashboards as ZIP files and capture screenshots.

Usage:
    python -m bi.setup.export_dashboards

Exports all 3 Mortality Analytics dashboards to:
    bi/dashboards/<dashboard_slug>.zip          — Full asset export
    bi/dashboards/<dashboard_slug>.png          — Dashboard screenshot

Environment variables (all optional):
    SUPERSET_URL  — Superset base URL (default http://localhost:8088)
    SUPERSET_USER — Superset admin user (default admin)
    SUPERSET_PASS — Superset admin password (default admin)
"""

import os
import sys
import time

from bi.setup.auth import authenticate
from bi.setup.client import api_get, api_post
from bi.setup.config import SUPERSET_URL, SUPERSET_USER, SUPERSET_PASS, DASHBOARDS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboards")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(title: str) -> str:
    """Derive a filesystem-safe slug from a dashboard title."""
    return title.lower().replace(" ", "_").replace("—", "-").replace("  ", "_")


def _find_dashboard_id(session, base_url: str, title: str) -> int:
    """Look up a dashboard ID by title."""
    url = f"{base_url}/api/v1/dashboard/"
    resp = api_get(session, url)
    resp.raise_for_status()
    results = resp.json().get("result", [])
    for db in results:
        if db.get("dashboard_title") == title:
            return db["id"]
    raise ValueError(f"Dashboard not found: {title}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_dashboard_zip(session, base_url: str, dash_id: int,
                          slug: str) -> str:
    """Export a dashboard as a ZIP file via the REST API.

    Returns:
        Absolute path to the saved ZIP file.
    """
    url = f"{base_url}/api/v1/dashboard/export/"
    params = {"q": f"[{dash_id}]"}
    resp = api_get(session, url, params=params)
    resp.raise_for_status()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{slug}.zip")
    with open(filepath, "wb") as fh:
        fh.write(resp.content)
    return filepath


def capture_dashboard_screenshot(session, base_url: str,
                                   dash_id: int, slug: str) -> str | None:
    """Request a dashboard screenshot and retrieve it.

    Uses the two-step process:
        1. POST /api/v1/dashboard/{id}/cache_dashboard_screenshot/
        2. GET  /api/v1/dashboard/{id}/thumbnail/{digest}/

    Returns:
        Path to the saved PNG, or None if screenshot generation failed.
    """
    # Step 1: trigger screenshot generation
    cache_url = (f"{base_url}/api/v1/dashboard/{dash_id}"
                 f"/cache_dashboard_screenshot/")
    try:
        cache_resp = api_post(session, cache_url)
        cache_resp.raise_for_status()
    except Exception as exc:
        print(f"  ⚠ Screenshot trigger failed for {slug}: {exc}")
        return None

    # Give the screenshot worker time to render
    time.sleep(3)

    # Step 2: retrieve the screenshot digest from dashboard detail
    detail_url = f"{base_url}/api/v1/dashboard/{dash_id}"
    detail_resp = api_get(session, detail_url)
    detail_resp.raise_for_status()
    detail = detail_resp.json()

    # The thumbnail URL digest may be in result.thumbnail_url
    result = detail.get("result", {})
    thumbnail_url = result.get("thumbnail_url", "")

    if not thumbnail_url:
        print(f"  ⚠ No thumbnail URL for {slug}")
        return None

    # Extract digest from the URL: /api/v1/dashboard/{id}/thumbnail/{digest}/
    try:
        digest = thumbnail_url.rstrip("/").split("/")[-1]
    except (IndexError, AttributeError):
        print(f"  ⚠ Could not parse digest from {thumbnail_url}")
        return None

    # Step 2b: download the screenshot
    thumb_url = f"{base_url}/api/v1/dashboard/{dash_id}/thumbnail/{digest}/"
    thumb_resp = api_get(session, thumb_url)
    thumb_resp.raise_for_status()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{slug}.png")
    with open(filepath, "wb") as fh:
        fh.write(thumb_resp.content)
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_export() -> dict:
    """Export all dashboards as ZIP files and capture screenshots.

    Returns:
        dict mapping dashboard title → {"zip": path, "screenshot": path | None}
    """
    print(f"=== Superset Export: {SUPERSET_URL} ===")

    auth = authenticate(SUPERSET_URL, SUPERSET_USER, SUPERSET_PASS)
    session = auth["session"]
    base_url = SUPERSET_URL

    results = {}
    for title in DASHBOARDS:
        slug = _slug(title)
        print(f"\n--- Exporting: {title} ---")

        try:
            dash_id = _find_dashboard_id(session, base_url, title)
            print(f"  Dashboard ID: {dash_id}")

            # Export ZIP
            zip_path = export_dashboard_zip(session, base_url, dash_id, slug)
            print(f"  ✓ ZIP: {zip_path}")

            # Screenshot
            ss_path = capture_dashboard_screenshot(
                session, base_url, dash_id, slug,
            )
            if ss_path:
                print(f"  ✓ Screenshot: {ss_path}")

            results[title] = {"zip": zip_path, "screenshot": ss_path}

        except Exception as exc:
            print(f"  ✗ Failed: {exc}")
            results[title] = {"zip": None, "screenshot": None, "error": str(exc)}

    print(f"\n=== Export Complete → {OUTPUT_DIR} ===")
    return results


if __name__ == "__main__":
    try:
        run_export()
    except Exception as exc:
        print(f"\n✗ Export failed: {exc}", file=sys.stderr)
        sys.exit(1)
