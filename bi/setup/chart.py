"""Chart functions for Apache Superset REST API.

Creates and manages chart slices (visualizations) with their
parameterised configurations for dashboards.
"""

import json
import requests

from bi.setup.client import api_get, api_get_all, api_post, api_put


def create_chart(
    session: requests.Session,
    base_url: str,
    chart_config: dict,
) -> int:
    """Create a new chart (slice) in Superset.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        chart_config: Chart configuration dict with keys:
            - slice_name (str): Chart title.
            - viz_type (str): Visualisation type (e.g. echarts_timeseries_bar).
            - datasource_id (int): Dataset ID to query.
            - datasource_type (str): "table" for datasets.
            - params (str): JSON string of viz parameters.

    Returns:
        The newly created chart ID.

    Raises:
        requests.HTTPError: On creation failure.
    """
    url = f"{base_url}/api/v1/chart/"
    payload = {
        "slice_name": chart_config["slice_name"],
        "viz_type": chart_config["viz_type"],
        "datasource_id": chart_config["datasource_id"],
        "datasource_type": chart_config.get("datasource_type", "table"),
        "params": _serialize_params(chart_config.get("params", {})),
    }
    resp = api_post(session, url, json_data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def find_chart_by_name(
    session: requests.Session,
    base_url: str,
    slice_name: str | list[str],
    datasource_id: int | None = None,
    datasource_type: str | None = None,
) -> int | None:
    """Find a chart by its slice name (title).

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        slice_name: Chart title to search for.

    Returns:
        Chart ID if found, None otherwise.
    """
    names = [slice_name] if isinstance(slice_name, str) else slice_name
    url = f"{base_url}/api/v1/chart/"
    charts = api_get_all(session, url)
    for name in names:
        for chart in charts:
            if chart.get("slice_name") != name:
                continue
            if _matches_datasource(
                session,
                base_url,
                chart,
                datasource_id=datasource_id,
                datasource_type=datasource_type,
            ):
                return chart["id"]
    return None


def get_or_create_chart(
    session: requests.Session,
    base_url: str,
    chart_config: dict,
) -> int:
    """Retrieve an existing chart or create it if missing (idempotent).

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        chart_config: Chart configuration dict (see create_chart).

    Returns:
        Chart ID (existing or newly created).
    """
    names = [chart_config["slice_name"], *chart_config.get("legacy_slice_names", [])]
    existing = find_chart_by_name(
        session,
        base_url,
        names,
        datasource_id=chart_config["datasource_id"],
        datasource_type=chart_config.get("datasource_type", "table"),
    )
    if existing is not None:
        update_chart(session, base_url, existing, chart_config)
        return existing
    return create_chart(session, base_url, chart_config)


def update_chart(
    session: requests.Session,
    base_url: str,
    chart_id: int,
    chart_config: dict,
) -> int:
    """Update an existing chart so setup remains reproducible.

    Superset's API keeps existing slices when they are found by name. Without
    this update step, changing a chart from a table to a richer visualization in
    code would not affect an already-created local Superset instance.
    """
    url = f"{base_url}/api/v1/chart/{chart_id}"
    payload = {
        "slice_name": chart_config["slice_name"],
        "viz_type": chart_config["viz_type"],
        "datasource_id": chart_config["datasource_id"],
        "datasource_type": chart_config.get("datasource_type", "table"),
        "params": _serialize_params(chart_config.get("params", {})),
        "query_context": "{}",
        "query_context_generation": False,
    }
    resp = api_put(session, url, json_data=payload)
    resp.raise_for_status()
    return chart_id


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _serialize_params(params) -> str:
    """Convert params to a JSON string for the Superset API.

    The Superset REST API expects the ``params`` field as a JSON-encoded
    string, not a nested object.
    """
    if isinstance(params, str):
        return params
    return json.dumps(params, ensure_ascii=False)


def _matches_datasource(
    session: requests.Session,
    base_url: str,
    chart_row: dict,
    datasource_id: int | None,
    datasource_type: str | None,
) -> bool:
    """Return whether a chart belongs to the expected datasource.

    Superset list rows differ across versions. Prefer fields available on the
    list response, and fall back to the detail endpoint for ambiguous rows.
    """
    if datasource_id is None:
        return True

    row_datasource_id = chart_row.get("datasource_id")
    row_datasource_type = chart_row.get("datasource_type")
    if row_datasource_id is not None:
        return (
            row_datasource_id == datasource_id
            and (datasource_type is None or row_datasource_type in (None, datasource_type))
        )

    detail_url = f"{base_url}/api/v1/chart/{chart_row['id']}"
    resp = api_get(session, detail_url)
    resp.raise_for_status()
    detail = resp.json().get("result", {})
    detail_datasource_id = detail.get("datasource_id")
    detail_datasource_type = detail.get("datasource_type")
    return (
        detail_datasource_id == datasource_id
        and (datasource_type is None or detail_datasource_type == datasource_type)
    )
