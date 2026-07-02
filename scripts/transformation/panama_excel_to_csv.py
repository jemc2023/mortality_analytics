"""Convert Panama INEC mortality workbooks into wide CSVs.

The exported CSVs match the official layout used by INEC:

    Código;Sexo;Menores de 1;1;2;3;4;5 a 9;...;No especificada

Only real cause rows are kept. Aggregate subtotal rows such as `001-025` or
`026-046` are skipped, and only `Hombres` / `Mujeres` rows are emitted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw" / "panama"
OUTPUT_SUFFIX = "_csv.csv"
OUTPUT_DIR = RAW_DIR / "csv"

SUMMARY_CODE_RE = re.compile(r"^\d{2,3}-\d{2,3}$")
REAL_CODE_RE = re.compile(
    r"^(?:"
    r"\d{3}|"
    r"\d{3}-\d{3}|"
    r"\d{3}\s+y\s+\d{3}|"
    r"[A-Z]\d{2}(?:-[A-Z]?\d{2})?|"
    r"\d\.\d{2}|"
    r"\d{2}[A-Z]"
    r")$"
)
SEX_VALUES = {"hombres": "Hombres", "mujeres": "Mujeres"}


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value)
    text = re.sub(r"[.…]{2,}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_age_label(value: object) -> str:
    text = _clean_text(value)
    text = re.sub(r"\s*[-–]\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_sex(value: object) -> str:
    return SEX_VALUES.get(_clean_text(value).lower(), "")


def _is_summary_code(value: object) -> bool:
    code = _clean_text(value)
    if not code:
        return False
    return code.upper() == "TOTAL" or bool(SUMMARY_CODE_RE.match(code))


def _is_real_code(value: object) -> bool:
    code = _clean_text(value)
    if not code:
        return False
    lowered = code.lower()
    if "código" in lowered or "codigo" in lowered:
        return False
    if lowered in {"total", "hombres", "mujeres"}:
        return False
    return bool(REAL_CODE_RE.match(code))


def _is_granular_header(label: str) -> bool:
    return bool(
        re.fullmatch(r"\d", label)
        or re.fullmatch(r"\d+\s*a\s*\d+", label)
        or label.lower() in {"menores de 1", "1 a 4"}
    )


def _select_header_row(sheet: pd.DataFrame) -> int:
    candidates = [4, 5]
    best_row = None
    best_score = -1
    for row_idx in candidates:
        if row_idx >= sheet.shape[0]:
            continue

        header_row = sheet.iloc[row_idx]
        labels = []
        for col_idx in range(3, sheet.shape[1]):
            label = _normalize_age_label(header_row.iat[col_idx])
            if label and label.lower() not in {"total", "grupos de edad"}:
                labels.append(label)

        score = sum(1 for label in labels if _is_granular_header(label))
        if score > best_score or (score == best_score and best_row is not None and row_idx > best_row):
            best_score = score
            best_row = row_idx

    return best_row if best_row is not None else (5 if sheet.shape[0] > 5 else 4)


def _extract_age_columns(sheet: pd.DataFrame, year: int) -> list[tuple[int, str]]:
    if year == 2015:
        # 2015 is the only workbook where the first age block is split across
        # two header rows: row 5 carries 0-4 and row 4 carries the extra
        # grouped bucket for menores de 5.
        labels = []
        first_row = sheet.iloc[5]
        second_row = sheet.iloc[4]
        for col_idx in range(4, 9):
            label = _normalize_age_label(first_row.iat[col_idx])
            if label:
                labels.append((col_idx - 1, label))
        labels.append((8, "Menores de 5"))
        for col_idx in range(9, sheet.shape[1]):
            label = _normalize_age_label(second_row.iat[col_idx])
            if label and label.lower() not in {"total", "grupos de edad", "menores de 5"}:
                labels.append((col_idx, label))
        return labels

    header_row_index = _select_header_row(sheet)
    if sheet.shape[0] <= header_row_index:
        return []

    age_columns: list[tuple[int, str]] = []
    header_row = sheet.iloc[header_row_index]

    # The first three source columns are code, description and total.
    for col_idx in range(3, sheet.shape[1]):
        label = _normalize_age_label(header_row.iat[col_idx])
        if not label or label.lower() in {"total", "grupos de edad"}:
            continue
        age_columns.append((col_idx, label))

    return age_columns


def _to_value(cell: object) -> str:
    if pd.isna(cell):
        return "0"

    number = pd.to_numeric(cell, errors="coerce")
    if pd.notna(number):
        if float(number).is_integer():
            return str(int(number))
        return str(float(number))

    cleaned = _clean_text(cell)
    return "0" if cleaned in {"", "-", ".."} else cleaned


def _build_rows(sheet: pd.DataFrame, year: int) -> list[dict]:
    age_columns = _extract_age_columns(sheet, year)
    rows: list[dict] = []

    current_code = ""

    for row_idx in range(6, sheet.shape[0]):
        row = sheet.iloc[row_idx]
        code = _clean_text(row.iat[0])
        sex = _normalize_sex(row.iat[1])

        if code:
            lowered = code.lower()
            if (
                "código" in lowered
                or "codigo" in lowered
                or lowered in {"total", "hombres", "mujeres"}
                or _is_summary_code(code)
            ):
                current_code = ""
                continue

            if not _is_real_code(code):
                continue

            current_code = code
            continue

        if not current_code or not sex:
            continue

        values = [
            _to_value(row.iat[col_idx])
            for col_idx, _ in age_columns
        ]

        rows.append(
            {
                "Código": current_code,
                "Sexo": sex,
                **{label: value for (_, label), value in zip(age_columns, values)},
            }
        )

    return rows


def _read_workbook(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, header=None)


def _discover_input_files() -> list[Path]:
    return sorted(
        path
        for path in RAW_DIR.glob("panama_*.*")
        if path.suffix.lower() in {".xls", ".xlsx"}
    )


def _convert_workbook(path: Path) -> pd.DataFrame:
    year = int(path.stem.split("_")[-1])
    sheet = _read_workbook(path)
    rows = _build_rows(sheet, year)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _output_path_for(input_path: Path) -> Path:
    return OUTPUT_DIR / f"{input_path.stem}{OUTPUT_SUFFIX}"


def _write_csv(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, sep=";", encoding="utf-8")


def main() -> None:
    input_files = _discover_input_files()
    if not input_files:
        raise FileNotFoundError(f"No Panama workbooks found in {RAW_DIR}")

    for input_path in input_files:
        output_path = _output_path_for(input_path)
        df = _convert_workbook(input_path)
        if df.empty:
            raise ValueError(f"No rows extracted from {input_path.name}")

        _write_csv(df, output_path)
        print(f"Converted {input_path.name} -> {output_path.name} ({len(df):,} rows)")


if __name__ == "__main__":
    main()
