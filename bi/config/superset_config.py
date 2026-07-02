"""
superset_config.py — Apache Superset minimal single-container configuration.

Metadata database: SQLite (no PostgreSQL, no Redis required).
Greenplum data source connection configured via Superset UI:
    postgresql://gpadmin:semis2_grupo11@dw-greenplum:5432/dw_semis2
"""

import os
import secrets


# ---- Security ----
# Required for production. Override via SUPERSET_SECRET_KEY env var.
SECRET_KEY = os.environ.get(
    'SUPERSET_SECRET_KEY',
    secrets.token_hex(32),
)

# ---- Metadata Database ----
# SQLite metadata store (dashboards, charts, datasets, users, etc.)
# check_same_thread=false is required for threaded WSGI servers.
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'SUPERSET_DATABASE_URI',
    'sqlite:////app/superset_home/superset.db?check_same_thread=false',
)

# ---- CSRF Protection ----
WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = []
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 365  # 1 year

# ---- Query Limits ----
ROW_LIMIT = 5000

# ---- Feature Flags ----
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
}

# ---- Mapbox ----
# Set your token for deck.gl map visualizations.
MAPBOX_API_KEY = ''
