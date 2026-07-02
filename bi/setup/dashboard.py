"""Dashboard functions for Apache Superset REST API.

Creates dashboards and places charts within them using the position
layout mechanism.
"""

import json
import requests

from bi.setup.client import api_get, api_get_all, api_post, api_put


def create_dashboard(
    session: requests.Session,
    base_url: str,
    dashboard_title: str,
) -> int:
    """Create a new dashboard in Superset.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        dashboard_title: Display title for the dashboard.

    Returns:
        The newly created dashboard ID.

    Raises:
        requests.HTTPError: On creation failure.
    """
    url = f"{base_url}/api/v1/dashboard/"
    payload = {"dashboard_title": dashboard_title}
    resp = api_post(session, url, json_data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def find_dashboard_by_title(
    session: requests.Session,
    base_url: str,
    title: str,
) -> int | None:
    """Find a dashboard by its title.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        title: Dashboard title to search for.

    Returns:
        Dashboard ID if found, None otherwise.
    """
    url = f"{base_url}/api/v1/dashboard/"
    for db in api_get_all(session, url):
        if db.get("dashboard_title") == title:
            return db["id"]
    return None


def get_or_create_dashboard(
    session: requests.Session,
    base_url: str,
    dashboard_title: str,
) -> int:
    """Retrieve an existing dashboard or create it if missing (idempotent).

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        dashboard_title: Dashboard title.

    Returns:
        Dashboard ID (existing or newly created).
    """
    existing = find_dashboard_by_title(session, base_url, title=dashboard_title)
    if existing is not None:
        return existing
    return create_dashboard(session, base_url, dashboard_title)


def add_charts_to_dashboard(
    session: requests.Session,
    base_url: str,
    dashboard_id: int,
    chart_positions: list[dict],
) -> int:
    """Place charts onto a dashboard with specified layout positions.

    Fetches the current dashboard payload first, then updates only the
    ``position_json`` field — preserving ``dashboard_title`` and any
    other metadata already set on the dashboard.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        dashboard_id: The dashboard to update.
        chart_positions: List of position descriptors, each a dict with:
            - chart_id (int): Chart to place.
            - width (int, optional): Grid columns (1-12, default 6).
            - height (int, optional): Grid row units (default 50).
            - slice_name (str, optional): Override chart title on dashboard.

    Returns:
        The dashboard ID.

    Raises:
        requests.HTTPError: If the dashboard fetch or update fails.
    """
    # Fetch existing dashboard to preserve title and metadata
    detail_url = f"{base_url}/api/v1/dashboard/{dashboard_id}"
    detail_resp = api_get(session, detail_url)
    detail_resp.raise_for_status()
    existing = detail_resp.json().get("result", {})

    position_json = _build_position_json(chart_positions)

    # Merge new position with preserved fields
    payload = {
        "dashboard_title": existing.get("dashboard_title", ""),
        "slug": existing.get("slug"),
        "position_json": json.dumps(position_json),
        "json_metadata": existing.get("json_metadata", "{}"),
    }
    # Remove None-valued optional keys
    payload = {k: v for k, v in payload.items() if v is not None}

    update_url = f"{base_url}/api/v1/dashboard/{dashboard_id}"
    resp = api_put(session, update_url, json_data=payload)
    resp.raise_for_status()
    return dashboard_id


# ------------------------------------------------------------------
# Layout helpers
# ------------------------------------------------------------------

def _build_position_json(chart_positions: list[dict]) -> dict:
    """Construct a simple grid-based position_json for the dashboard.

    Places charts in a single-column layout, one chart per row, with
    configurable width and height. The root structure uses a tab + grid
    container as expected by modern Superset versions.
    """
    root_id = "ROOT_ID"
    tabs_id = "TABS-ROOT"
    tab_id = "TAB-DEFAULT"
    grid_id = "GRID-DEFAULT"

    position: dict = {
        root_id: {
            "id": root_id,
            "type": "ROOT",
            "children": [tabs_id],
        },
        tabs_id: {
            "id": tabs_id,
            "type": "TABS",
            "children": [tab_id],
        },
        tab_id: {
            "id": tab_id,
            "type": "TAB",
            "meta": {"text": "Overview"},
            "children": [grid_id],
        },
        grid_id: {
            "id": grid_id,
            "type": "GRID",
            "children": [],
        },
    }

    row_height = 50
    current_row = 0

    for i, pos in enumerate(chart_positions):
        chart_id = pos["chart_id"]
        width = pos.get("width", 12)
        height = pos.get("height", 50)

        # Each chart goes in its own row for a clean vertical stack
        row_id = f"ROW-{i}"
        chart_node_id = f"CHART-{chart_id}"

        row_top = current_row * row_height
        current_row += 1

        position[row_id] = {
            "id": row_id,
            "type": "ROW",
            "children": [chart_node_id],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        position[chart_node_id] = {
            "id": chart_node_id,
            "type": "CHART",
            "meta": {
                "chartId": chart_id,
                "width": width,
                "height": height,
                "uuid": f"chart-{chart_id}",
            },
        }
        position[grid_id]["children"].append(row_id)

    return position
