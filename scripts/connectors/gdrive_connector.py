import os
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from pyspark.sql.functions import lit

load_dotenv(Path(__file__).parents[2] / ".env")

SCOPES = ["https://www.googleapis.com/auth/drive"]
_DIR = Path(__file__).parent
_CREDENTIALS_FILE = _DIR / "gdrive_credentials.json"


def _service():
    client_id = os.getenv("GDRIVE_CLIENT_ID")
    client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("GDRIVE_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(_CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    return build("drive", "v3", credentials=creds)


def test_connection() -> None:
    about = _service().about().get(fields="user").execute()
    user = about["user"]
    print(f"Connected as: {user['displayName']} ({user['emailAddress']})")


def list_drive_files(folder_id: str = None, page_size: int = 50) -> list[dict]:
    query = f"'{folder_id}' in parents and trashed=false" if folder_id else "trashed=false"
    result = _service().files().list(
        q=query,
        pageSize=page_size,
        fields="files(id, name, mimeType, size, modifiedTime)",
    ).execute()
    return result.get("files", [])


def download_from_drive(file_id: str, destination: str) -> None:
    request = _service().files().get_media(fileId=file_id)
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    print(f"Downloaded: {file_id} → {destination}")


def upload_to_drive(local_path: str, folder_id: str = None, mime_type: str = "text/csv") -> str:
    name = Path(local_path).name
    metadata = {"name": name}
    if folder_id:
        metadata["parents"] = [folder_id]
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    file = _service().files().create(body=metadata, media_body=media, fields="id").execute()
    print(f"Uploaded: {name} → Drive (id={file['id']})")
    return file["id"]

def get_folder_id_by_name(folder_name: str, parent_id: str = None) -> str | None:
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    result = _service().files().list(
        q=query,
        fields="files(id, name)",
        pageSize=1
    ).execute()
    
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    
    print(f"No se encontró ninguna carpeta con el nombre: '{folder_name}'")
    return None

def get_file_id_by_name(file_name: str, folder_id: str = None) -> str | None:
    query = f"mimeType != 'application/vnd.google-apps.folder' and name = '{file_name}' and trashed = false"
    
    if folder_id:
        query += f" and '{folder_id}' in parents"
        
    result = _service().files().list(
        q=query,
        fields="files(id, name)",
        pageSize=1
    ).execute()
    
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    
    print(f"No se encontró ningún archivo con el nombre: '{file_name}'")
    return None

def list_files_in_folder(folder_id: str) -> list:
    query = f"mimeType != 'application/vnd.google-apps.folder' and '{folder_id}' in parents and trashed = false"
    result = _service().files().list(
        q=query,
        fields="files(id, name)",
        pageSize=100
    ).execute()
    return result.get("files", [])


def create_drive_folder(folder_name: str, parent_folder_id: str = None) -> str:
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]
        
    folder = _service().files().create(
        body=metadata, 
        fields="id"
    ).execute()
    
    print(f"Carpeta creada con éxito: '{folder_name}' → (id={folder['id']})")
    return folder["id"]


if __name__ == "__main__":
    test_connection()

    root_folder_id = get_folder_id_by_name("semis2_raw_data")
    ine_folder_id = get_folder_id_by_name("ine", root_folder_id)
    ine_files = list_files_in_folder(ine_folder_id)

    df_total = None

    for file in sorted(ine_files, key=lambda f: f["name"]):
        anio = int(file["name"].split("_")[-1].replace(".csv", ""))
        tmp_path = f"/Workspace/tmp/ine/{file['name']}"
        download_from_drive(file["id"], tmp_path)

        df_anio = spark.read.format("csv") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .option("sep", ",") \
            .load(f"file:{tmp_path}") \
            .withColumn("anio", lit(anio))

        df_total = df_anio if df_total is None else df_total.unionByName(df_anio, allowMissingColumns=True)

    df = df_total

    display(df)
    #Transformaciones...

    df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .saveAsTable("sandbox.raw_ine")
    
    
