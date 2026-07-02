import boto3
from pathlib import Path
from dotenv import load_dotenv

# load_dotenv(Path(__file__).parents[2] / ".env")

BUCKET = "mortality-analytics-semi2"
REGION = "us-east-1"


def _client():
    return boto3.client("s3", region_name=REGION)


def upload_file(local_path: str, s3_key: str) -> None:
    _client().upload_file(local_path, BUCKET, s3_key)
    print(f"Uploaded: {local_path} → s3://{BUCKET}/{s3_key}")


def download_file(s3_key: str, destination: str) -> None:
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    _client().download_file(BUCKET, s3_key, destination)
    print(f"Downloaded: s3://{BUCKET}/{s3_key} → {destination}")


def upload_folder(local_dir: str, s3_prefix: str) -> None:
    base = Path(local_dir)
    for path in base.rglob("*"):
        if path.is_file():
            upload_file(str(path), f"{s3_prefix}/{path.relative_to(base)}")


def list_files(prefix: str = "") -> list[dict]:
    paginator = _client().get_paginator("list_objects_v2")
    results = []
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            results.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "modified": str(obj["LastModified"]),
            })
    return results


def test_connection() -> None:
    print(f"Bucket: s3://{BUCKET}")
    files = list_files()
    print(f"Objects: {len(files)}")
    for f in files:
        print(f"  {f['key']} ({f['size']} bytes)")


if __name__ == "__main__":
    test_connection()
    download_file("raw/who/who_central_america.csv", "/home/theDevil/Downloads/s3.csv")