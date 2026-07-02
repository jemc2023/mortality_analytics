"""Setup utilities for Apache Superset — programmatic asset creation and export."""

from bi.setup.auth import authenticate
from bi.setup.client import SessionManager
from bi.setup.database import create_database_connection, get_or_create_database
from bi.setup.dataset import create_dataset, get_or_create_dataset
from bi.setup.chart import create_chart, get_or_create_chart
from bi.setup.dashboard import create_dashboard, get_or_create_dashboard, add_charts_to_dashboard

__all__ = [
    "authenticate",
    "SessionManager",
    "create_database_connection",
    "get_or_create_database",
    "create_dataset",
    "get_or_create_dataset",
    "create_chart",
    "get_or_create_chart",
    "create_dashboard",
    "get_or_create_dashboard",
    "add_charts_to_dashboard",
]
