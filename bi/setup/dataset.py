"""Dataset functions for Apache Superset REST API.

Creates and manages virtual datasets pointing to Greenplum tables/views
in the dm_mortality schema for charting and dashboard consumption.
"""

import requests

from bi.setup.client import api_get_all, api_post


def create_dataset(
    session: requests.Session,
    base_url: str,
    database_id: int,
    schema: str,
    table_name: str,
) -> int:
    """Register a physical table or view as a Superset dataset.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        database_id: The database connection ID to use.
        schema: Database schema (e.g. dm_mortality).
        table_name: Table or view name (e.g. v_ine_completa).

    Returns:
        The newly created dataset ID.

    Raises:
        requests.HTTPError: On creation failure (non-2xx, including
            409 Conflict if dataset already exists).
    """
    url = f"{base_url}/api/v1/dataset/"
    payload = {
        "database": database_id,
        "schema": schema,
        "table_name": table_name,
    }
    resp = api_post(session, url, json_data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def find_dataset_by_name(
    session: requests.Session,
    base_url: str,
    database_id: int,
    schema: str,
    table_name: str,
) -> int | None:
    """Find a dataset by its schema-qualified table name.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        database_id: Superset database connection ID.
        schema: Database schema name.
        table_name: Table or view name.

    Returns:
        Dataset ID if found, None otherwise.
    """
    # Filter by schema and table_name locally
    url = f"{base_url}/api/v1/dataset/"
    for r in api_get_all(session, url):
        if (
            r.get("schema") == schema
            and r.get("table_name") == table_name
            and _matches_database_id(r, database_id)
        ):
            return r["id"]
    return None


def get_or_create_dataset(
    session: requests.Session,
    base_url: str,
    database_id: int,
    schema: str,
    table_name: str,
) -> int:
    """Retrieve an existing dataset or create it if missing (idempotent).

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        database_id: The database connection ID.
        schema: Database schema.
        table_name: Table or view name.

    Returns:
        Dataset ID (existing or newly created).
    """
    existing = find_dataset_by_name(
        session, base_url, database_id, schema, table_name,
    )
    if existing is not None:
        return existing
    return create_dataset(session, base_url, database_id, schema, table_name)


def _matches_database_id(dataset_row: dict, database_id: int) -> bool:
    """Return whether a Superset dataset list row belongs to a database."""
    database = dataset_row.get("database")
    if isinstance(database, dict):
        return database.get("id") == database_id
    if isinstance(database, int):
        return database == database_id
    return dataset_row.get("database_id") == database_id
