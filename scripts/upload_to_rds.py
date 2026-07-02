"""
Carga los CSV de MSPAS al esquema raw_data de RDS PostgreSQL.
Cada CSV genera una tabla: raw_data.<nombre_archivo>
"""

import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

CSV_DIR = Path(__file__).parents[1] / "data" / "raw" / "mspas" / "extracted"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

with engine.connect() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw_data"))
    conn.commit()
    print("Schema raw_data listo.")

for csv_file in sorted(CSV_DIR.glob("*.csv")):
    table = csv_file.stem  # mspas_exceso_mortalidad_2022, etc.

    print(f"\nLeyendo {csv_file.name}...")
    df = pd.read_csv(csv_file, dtype=str, encoding="utf-8")

    print(f"  {len(df):,} filas, {len(df.columns)} columnas → raw_data.{table}")
    df.to_sql(
        name=table,
        schema="raw_data",
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi",
    )
    print(f"  raw_data.{table} creada correctamente.")

print("\nCarga completada.")
