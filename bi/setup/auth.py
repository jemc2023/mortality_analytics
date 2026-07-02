"""Authentication functions for Apache Superset REST API.

Provides JWT-based authentication and CSRF token retrieval required
for all state-changing API operations (POST, PUT, DELETE).
"""

import requests


def authenticate(base_url: str, username: str, password: str) -> dict:
    """Authenticate with Superset and retrieve access + CSRF tokens.

    Performs a two-step authentication:
        1. POST /api/v1/security/login to obtain a JWT access token.
        2. GET /api/v1/security/csrf_token/ to obtain a CSRF token.

    Args:
        base_url: Superset base URL (e.g. http://localhost:8088).
        username: Superset user name.
        password: Superset user password.

    Returns:
        dict with keys:
            - access_token (str): JWT bearer token.
            - csrf_token (str): CSRF protection token.
            - session (requests.Session): Configured session with auth
              headers pre-set for subsequent API calls.

    Raises:
        requests.HTTPError: If authentication fails (non-2xx response).
        requests.ConnectionError: If Superset is unreachable.
    """
    session = requests.Session()

    # Step 1: Obtain JWT via login
    login_url = f"{base_url}/api/v1/security/login"
    login_payload = {
        "username": username,
        "password": password,
        "provider": "db",
    }
    login_resp = session.post(login_url, json=login_payload)
    login_resp.raise_for_status()
    access_token = login_resp.json()["access_token"]

    # Set bearer token for subsequent calls
    session.headers.update({"Authorization": f"Bearer {access_token}"})

    # Step 2: Obtain CSRF token for state-changing requests
    csrf_url = f"{base_url}/api/v1/security/csrf_token/"
    csrf_resp = session.get(csrf_url)
    csrf_resp.raise_for_status()
    csrf_token = csrf_resp.json()["result"]

    # Set CSRF token header
    session.headers.update({"X-CSRFToken": csrf_token})

    return {
        "access_token": access_token,
        "csrf_token": csrf_token,
        "session": session,
    }
