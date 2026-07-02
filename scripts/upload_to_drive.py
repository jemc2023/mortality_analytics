"""
Sube todos los CSV de las 5 fuentes a la carpeta semis2_raw_data en Google Drive.
Crea subcarpetas por fuente si no existen.

Uso: python scripts/upload_to_drive.py
"""

from pathlib import Path
from connectors.gdrive_connector import (
    upload_to_drive,
    get_folder_id_by_name,
    create_drive_folder,
)

RAW_DIR = Path(__file__).parents[1] / "data" / "raw"

SOURCES = {
    "ine": [
        RAW_DIR / "ine" / "csv" / f"ine_defunciones_{year}.csv"
        for year in range(2015, 2025)
    ] + [
        RAW_DIR / "ine" / "csv" / "ine_diccionario_defunciones.csv",
        RAW_DIR / "ine" / "csv" / "ine_diccionario_cie-10.csv",
    ],
    "mspas": list((RAW_DIR / "mspas" / "extracted").glob("*.csv")),
    "panama": list((RAW_DIR / "panama" / "extracted").glob("*.csv")),
    "who": [RAW_DIR / "who" / "who_central_america.csv"],
    "ihme": list((RAW_DIR / "ihme").glob("*.csv")),
}


def _get_or_create_folder(name: str, parent_id: str) -> str:
    folder_id = get_folder_id_by_name(name, parent_id)
    if not folder_id:
        folder_id = create_drive_folder(name, parent_id)
    return folder_id


def main():
    root_id = get_folder_id_by_name("semis2_raw_data")
    if not root_id:
        raise RuntimeError("No se encontró la carpeta 'semis2_raw_data' en Drive.")

    for source, files in SOURCES.items():
        print(f"\n── {source.upper()} ──")
        subfolder_id = _get_or_create_folder(source, root_id)
        for path in sorted(files):
            if not path.exists():
                print(f"  SKIP (no existe): {path.name}")
                continue
            upload_to_drive(str(path), folder_id=subfolder_id)

    print("\nSubida completada.")


if __name__ == "__main__":
    main()
