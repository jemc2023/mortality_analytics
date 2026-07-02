"""Database connection functions for Apache Superset REST API.

Creates and manages Greenplum/PostgreSQL database connections that
Superset uses as data sources for charts and dashboards.
"""

import requests

from bi.setup.client import api_get, api_post


def create_database_connection(
    session: requests.Session,
    base_url: str,
    database_name: str,
    sqlalchemy_uri: str,
) -> int:
    """Create a new database connection in Superset.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        database_name: Display name for the database.
        sqlalchemy_uri: Connection string (e.g.
            postgresql://user:pass@host:port/dbname).

    Returns:
        The newly created database ID.

    Raises:
        requests.HTTPError: On creation failure (non-2xx).
    """
    url = f"{base_url}/api/v1/database/"
    payload = {
        "database_name": database_name,
        "sqlalchemy_uri": sqlalchemy_uri,
    }
    resp = api_post(session, url, json_data=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def find_database_by_name(
    session: requests.Session,
    base_url: str,
    database_name: str,
) -> int | None:
    """Find a database by its display name.

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        database_name: Name to search for.

    Returns:
        Database ID if found, None otherwise.
    """
    url = f"{base_url}/api/v1/database/"
    resp = api_get(session, url)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("result", [])
    for db in results:
        if db.get("database_name") == database_name:
            return db["id"]
    return None


def get_or_create_database(
    session: requests.Session,
    base_url: str,
    database_name: str,
    sqlalchemy_uri: str,
) -> int:
    """Retrieve an existing database or create it if missing (idempotent).

    Args:
        session: Authenticated requests.Session.
        base_url: Superset base URL.
        database_name: Display name for the database.
        sqlalchemy_uri: Connection string.

    Returns:
        Database ID (existing or newly created).
    """
    existing = find_database_by_name(session, base_url, database_name)
    if existing is not None:
        return existing
    return create_database_connection(
        session, base_url, database_name, sqlalchemy_uri,
    )
