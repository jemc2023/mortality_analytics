import os
import requests
import msal
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
SCOPES = [
    "https://graph.microsoft.com/Files.ReadWrite.All",
    "https://graph.microsoft.com/User.Read",
]
TOKEN_CACHE_FILE = Path(__file__).parent / ".sp_token_cache.bin"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_token() -> dict:
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_FILE.exists():
        cache.deserialize(TOKEN_CACHE_FILE.read_bytes().decode())

    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        token_cache=cache,
    )

    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

    TOKEN_CACHE_FILE.write_bytes(cache.serialize().encode())

    if "access_token" not in result:
        raise ValueError(f"Auth failed: {result.get('error_description', result)}")

    return result


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()['access_token']}"}


def test_connection() -> None:
    resp = requests.get(f"{GRAPH_BASE}/me", headers=_headers())
    resp.raise_for_status()
    me = resp.json()
    print(f"Connected as: {me.get('displayName')} ({me.get('userPrincipalName')})")


def list_onedrive_files(folder_path: str = "root") -> list[dict]:
    if folder_path == "root":
        url = f"{GRAPH_BASE}/me/drive/root/children"
    else:
        url = f"{GRAPH_BASE}/me/drive/root:/{folder_path}:/children"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    return [
        {"name": i["name"], "id": i["id"], "size": i.get("size")}
        for i in resp.json()["value"]
    ]


def download_from_onedrive(file_path: str, destination: str) -> None:
    url = f"{GRAPH_BASE}/me/drive/root:/{file_path}:/content"
    resp = requests.get(url, headers=_headers(), stream=True)
    resp.raise_for_status()
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {file_path} → {destination}")


def upload_to_onedrive(local_path: str, onedrive_folder: str = "semi2-mortalidad") -> None:
    name = Path(local_path).name
    url = f"{GRAPH_BASE}/me/drive/root:/{onedrive_folder}/{name}:/content"
    with open(local_path, "rb") as f:
        resp = requests.put(
            url,
            headers={**_headers(), "Content-Type": "application/octet-stream"},
            data=f,
        )
    resp.raise_for_status()
    print(f"Uploaded: {name} → OneDrive/{onedrive_folder}/")


if __name__ == "__main__":
    test_connection()
    download_from_onedrive("semi2-mortalidad/defunciones_2015.csv", "/home/theDevil/Downloads/oneDrive.csv")
    
    
    
    
