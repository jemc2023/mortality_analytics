"""Verify Panama CSV exports against the source Excel workbooks.

The script compares, per year, the generated wide CSV in
``data/raw/panama/csv/`` against the corresponding workbook in
``data/raw/panama/``.

It reports:
1. workbook summary total (when present)
2. workbook detailed total from real cause rows
3. CSV total
4. per-code mismatches, if any
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "panama"
CSV_DIR = RAW_DIR / "csv"

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


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _is_real_code(value: object) -> bool:
    code = _clean(value)
    if not code:
        return False
    lowered = code.lower()
    if "código" in lowered or "codigo" in lowered or lowered in {"total", "hombres", "mujeres"}:
        return False
    return bool(REAL_CODE_RE.match(code))


def _workbook_path(year: int) -> Path:
    candidates = [
        path for path in RAW_DIR.glob(f"panama_{year}.*")
        if path.suffix.lower() in {".xls", ".xlsx"}
    ]
    if not candidates:
        raise FileNotFoundError(f"No workbook found for year {year}")
    return candidates[0]


def _csv_path(year: int) -> Path:
    path = CSV_DIR / f"panama_{year}_csv.csv"
    if not path.exists():
        raise FileNotFoundError(f"No CSV found for year {year}: {path}")
    return path


def _extract_workbook_totals(path: Path) -> tuple[dict[str, float], float | None]:
    df = pd.read_excel(path, header=None)
    totals: dict[str, float] = {}
    current_code: str | None = None
    summary_total: float | None = None

    for idx in range(6, len(df)):
        code = _clean(df.iat[idx, 0])
        sex = _clean(df.iat[idx, 1]).lower()

        if code:
            lowered = code.lower()
            if "total" in lowered and summary_total is None:
                summary_total = pd.to_numeric(df.iat[idx, 2], errors="coerce")
                current_code = None
                continue
            if (
                "código" in lowered
                or "codigo" in lowered
                or lowered in {"total", "hombres", "mujeres"}
                or SUMMARY_CODE_RE.match(code)
            ):
                current_code = None
                continue
            if not _is_real_code(code):
                continue

            current_code = code
            continue

        if current_code and (sex.startswith("hombres") or sex.startswith("mujeres")):
            row_total = 0.0
            for col_idx in range(3, df.shape[1]):
                value = pd.to_numeric(df.iat[idx, col_idx], errors="coerce")
                if pd.notna(value):
                    row_total += float(value)
            totals[current_code] = totals.get(current_code, 0.0) + row_total

    return totals, (float(summary_total) if summary_total is not None and pd.notna(summary_total) else None)


def _extract_csv_totals(path: Path) -> dict[str, float]:
    df = pd.read_csv(path, sep=";", dtype=str)
    age_columns = [col for col in df.columns if col not in {"Código", "Sexo"}]
    return (
        df.groupby("Código")[age_columns]
        .apply(lambda group: group.apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum())
        .to_dict()
    )


def _years_to_check(explicit_years: list[int] | None) -> list[int]:
    if explicit_years:
        return explicit_years
    return sorted(
        int(path.stem.split("_")[1])
        for path in CSV_DIR.glob("panama_*_csv.csv")
    )


def verify_year(year: int) -> int:
    workbook_path = _workbook_path(year)
    csv_path = _csv_path(year)

    workbook_totals, workbook_summary = _extract_workbook_totals(workbook_path)
    csv_totals = _extract_csv_totals(csv_path)

    workbook_total = sum(workbook_totals.values())
    csv_total = sum(csv_totals.values())

    diffs = [
        (code, int(workbook_totals.get(code, 0)), int(csv_totals.get(code, 0)))
        for code in sorted(set(workbook_totals) | set(csv_totals), key=str)
        if int(workbook_totals.get(code, 0)) != int(csv_totals.get(code, 0))
    ]

    print(f"\n{year}")
    print(f"  workbook_summary_total: {int(workbook_summary) if workbook_summary is not None else 'n/a'}")
    print(f"  workbook_detail_total : {int(workbook_total)}")
    print(f"  csv_total             : {int(csv_total)}")
    print(f"  diff                  : {int(csv_total - workbook_total)}")

    if diffs:
        print("  mismatched codes:")
        for code, wb_total, csv_code_total in diffs[:15]:
            print(f"    - {code}: workbook={wb_total} csv={csv_code_total}")
        if len(diffs) > 15:
            print(f"    ... {len(diffs) - 15} more")
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Panama CSV exports against Excel workbooks")
    parser.add_argument("years", nargs="*", type=int, help="Optional years to verify")
    args = parser.parse_args()

    years = _years_to_check(args.years)
    if not years:
        raise FileNotFoundError(f"No generated Panama CSVs found in {CSV_DIR}")

    failures = 0
    for year in years:
        failures += verify_year(year)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
