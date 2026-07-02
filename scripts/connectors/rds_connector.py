import hashlib
import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mortality_dw")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "admin123")

_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def _engine():
    return create_engine(_CONNECTION_STRING)


def test_connection() -> None:
    with _engine().connect() as conn:
        row = conn.execute(text("SELECT version()")).fetchone()
        print(f"Connected to: {row[0]}")


def query(sql: str, params: dict = None) -> pd.DataFrame:
    return pd.read_sql(sql, _engine(), params=params)


def load_to_sandbox(df: pd.DataFrame, source: str, source_file: str) -> int:
    df = df.copy()
    df["source"] = source
    df["source_file"] = Path(source_file).name
    df["record_hash"] = df.apply(
        lambda r: hashlib.sha256(str(r.values).encode()).hexdigest(), axis=1
    )
    engine = _engine()
    with engine.connect() as conn:
        existing = pd.read_sql(
            "SELECT record_hash FROM sandbox.defunciones_raw WHERE source = %(src)s",
            conn,
            params={"src": source},
        )
        new_rows = df[~df["record_hash"].isin(existing["record_hash"])]

    if new_rows.empty:
        print(f"No new rows for source '{source}'")
        return 0

    new_rows.to_sql("defunciones_raw", engine, schema="raw_data", if_exists="append", index=False)
    print(f"Loaded {len(new_rows)} rows from '{source}' into raw_data.defunciones_2015")
    return len(new_rows)


def sandbox_summary() -> None:
    df = query("""
        SELECT *
        FROM raw_data.defunciones_2015
        LIMIT 5;
    """)
    if df.empty:
        print("Sandbox is empty.")
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    test_connection()
    print("\nSandbox summary:")
    sandbox_summary()
