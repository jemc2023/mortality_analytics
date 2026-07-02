from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests


DEFAULT_CONFIG = Path(__file__).with_name("tables.json")
DEFAULT_TABLE = "semi2.dm_mortality.dim_genero"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){1,2}$")
IDENTIFIER_PART_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
STATEMENT_WAIT_TIMEOUT = os.getenv("DATABRICKS_STATEMENT_WAIT_TIMEOUT", "30s")
STATEMENT_POLL_SECONDS = float(os.getenv("DATABRICKS_STATEMENT_POLL_SECONDS", "2"))
STATEMENT_MAX_WAIT_SECONDS = int(os.getenv("DATABRICKS_STATEMENT_MAX_WAIT_SECONDS", "120"))
EXTERNAL_LINK_TIMEOUT_SECONDS = int(os.getenv("DATABRICKS_EXTERNAL_LINK_TIMEOUT_SECONDS", "120"))


@dataclass(frozen=True)
class TableMapping:
    source_table: str
    target_table: str
    group: str
    partition_column: str | None = None
    partition_strategy: str = "value"
    partition_range_size: int | None = None


@dataclass(frozen=True)
class ReplicationConfig:
    mode: str
    tables: tuple[TableMapping, ...]


@dataclass(frozen=True)
class DatabricksResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]


def load_config(path: Path) -> ReplicationConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tables = tuple(
            TableMapping(
                source_table=item["source_table"],
                target_table=item["target_table"],
                group=item.get("group", "default"),
                partition_column=item.get("partition_column"),
                partition_strategy=item.get("partition_strategy", "value"),
                partition_range_size=item.get("partition_range_size"),
            )
        for item in payload.get("tables", [])
    )
    return ReplicationConfig(mode=payload.get("mode", "full_refresh"), tables=tables)


def missing_databricks_settings() -> list[str]:
    required = ["DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_HTTP_PATH"]
    return [name for name in required if not os.getenv(name)]


def missing_greenplum_settings() -> list[str]:
    required = ["GREENPLUM_HOST", "GREENPLUM_PORT", "GREENPLUM_DB", "GREENPLUM_USER"]
    return [name for name in required if not os.getenv(name)]


def preflight(config: ReplicationConfig) -> dict[str, Any]:
    return {
        "mode": config.mode,
        "tables": len(config.tables),
        "missing_databricks_settings": missing_databricks_settings(),
        "missing_greenplum_settings": missing_greenplum_settings(),
        "databricks_transport": "statement_execution_api",
        "databricks_connection_status": "configured" if not missing_databricks_settings() else "missing_settings",
    }


def run_preflight(config_path: Path) -> int:
    print(json.dumps(preflight(load_config(config_path)), indent=2, ensure_ascii=False))
    return 0


def log_step(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def normalize_databricks_host(value: str) -> str:
    return value.removeprefix("https://").removeprefix("http://").rstrip("/")


def databricks_base_url() -> str:
    return f"https://{normalize_databricks_host(os.environ['DATABRICKS_HOST'])}"


def databricks_warehouse_id() -> str:
    return os.environ["DATABRICKS_HTTP_PATH"].rstrip("/").split("/")[-1]


def databricks_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['DATABRICKS_TOKEN']}",
        "Content-Type": "application/json",
    }


def validate_table_name(table_name: str) -> str:
    if not IDENTIFIER_PATTERN.match(table_name):
        raise ValueError(f"Invalid table identifier: {table_name}")
    return table_name


def quote_databricks_identifier(table_name: str) -> str:
    validate_table_name(table_name)
    return ".".join(f"`{part}`" for part in table_name.split("."))


def quote_databricks_column(column_name: str) -> str:
    if not IDENTIFIER_PART_PATTERN.match(column_name):
        raise ValueError(f"Invalid column identifier: {column_name}")
    return f"`{column_name}`"


def quote_greenplum_identifier(table_name: str) -> str:
    validate_table_name(table_name)
    return ".".join(f'"{part}"' for part in table_name.split("."))


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def submit_databricks_statement(statement: str, disposition: str = "INLINE") -> dict[str, Any]:
    response = requests.post(
        f"{databricks_base_url()}/api/2.0/sql/statements/",
        headers=databricks_headers(),
        json={
            "warehouse_id": databricks_warehouse_id(),
            "statement": statement,
            "disposition": disposition,
            "format": "JSON_ARRAY",
            "wait_timeout": STATEMENT_WAIT_TIMEOUT,
            "on_wait_timeout": "CONTINUE",
        },
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def get_databricks_statement(statement_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{databricks_base_url()}/api/2.0/sql/statements/{statement_id}",
        headers=databricks_headers(),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def wait_for_statement(payload: dict[str, Any]) -> dict[str, Any]:
    statement_id = payload.get("statement_id")
    start = time.monotonic()
    current = payload

    while current.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        if not statement_id:
            raise RuntimeError(f"Databricks statement did not return statement_id: {current}")
        if time.monotonic() - start > STATEMENT_MAX_WAIT_SECONDS:
            raise TimeoutError(f"Databricks statement timed out after {STATEMENT_MAX_WAIT_SECONDS}s: {statement_id}")
        time.sleep(STATEMENT_POLL_SECONDS)
        current = get_databricks_statement(statement_id)

    state = current.get("status", {}).get("state")
    if state != "SUCCEEDED":
        error = current.get("status", {}).get("error", {})
        raise RuntimeError(f"Databricks statement failed with state {state}: {error}")
    return current


def get_databricks_chunk(statement_id: str, chunk_index: int) -> dict[str, Any]:
    response = requests.get(
        f"{databricks_base_url()}/api/2.0/sql/statements/{statement_id}/result/chunks/{chunk_index}",
        headers=databricks_headers(),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def download_external_json_rows(external_link: str) -> list[tuple[Any, ...]]:
    response = requests.get(external_link, timeout=EXTERNAL_LINK_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    return [tuple(row) for row in payload]


def collect_external_rows(result: dict[str, Any]) -> list[tuple[Any, ...]]:
    statement_id = result["statement_id"]
    chunk = result.get("result", {})
    rows: list[tuple[Any, ...]] = []

    while True:
        for item in chunk.get("external_links", []):
            rows.extend(download_external_json_rows(item["external_link"]))

        next_chunk_index = chunk.get("next_chunk_index")
        if next_chunk_index is None:
            break
        chunk = get_databricks_chunk(statement_id, int(next_chunk_index)).get("result", {})

    return rows


def execute_databricks_query(statement: str, disposition: str = "INLINE") -> DatabricksResult:
    result = wait_for_statement(submit_databricks_statement(statement, disposition=disposition))
    manifest = result.get("manifest", {})
    columns = [column["name"] for column in manifest.get("schema", {}).get("columns", [])]
    if manifest.get("truncated"):
        raise RuntimeError("Databricks result was truncated; increase byte_limit or partition the query")

    if disposition == "EXTERNAL_LINKS":
        return DatabricksResult(columns=columns, rows=collect_external_rows(result))

    data = result.get("result", {}).get("data_array", [])
    return DatabricksResult(columns=columns, rows=[tuple(row) for row in data])


def greenplum_connection() -> Any:
    import psycopg2

    return psycopg2.connect(
        host=os.environ["GREENPLUM_HOST"],
        port=os.environ["GREENPLUM_PORT"],
        dbname=os.environ["GREENPLUM_DB"],
        user=os.environ["GREENPLUM_USER"],
        password=os.getenv("PGPASSWORD"),
    )


def fetch_databricks_table(table_name: str, limit: int | None = None) -> tuple[list[str], list[tuple[Any, ...]]]:
    query = f"SELECT * FROM {quote_databricks_identifier(table_name)}"
    if limit is not None:
        query = f"{query} LIMIT {int(limit)}"
    disposition = "INLINE" if limit is not None else "EXTERNAL_LINKS"
    result = execute_databricks_query(query, disposition=disposition)
    return result.columns, result.rows


def fetch_databricks_partition_values(table_name: str, partition_column: str) -> list[Any]:
    result = execute_databricks_query(
        f"""
        SELECT DISTINCT {quote_databricks_column(partition_column)} AS partition_value
        FROM {quote_databricks_identifier(table_name)}
        ORDER BY partition_value
        """
    )
    return [row[0] for row in result.rows]


def fetch_databricks_partition_ranges(table_name: str, partition_column: str, range_size: int) -> list[tuple[int, int]]:
    if range_size <= 0:
        raise ValueError(f"partition_range_size must be greater than 0 for {table_name}")
    result = execute_databricks_query(
        f"""
        SELECT
          MIN({quote_databricks_column(partition_column)}) AS min_value,
          MAX({quote_databricks_column(partition_column)}) AS max_value
        FROM {quote_databricks_identifier(table_name)}
        WHERE {quote_databricks_column(partition_column)} IS NOT NULL
        """
    )
    if not result.rows or result.rows[0][0] is None or result.rows[0][1] is None:
        return []
    min_value = int(result.rows[0][0])
    max_value = int(result.rows[0][1])
    return [(start, min(start + range_size - 1, max_value)) for start in range(min_value, max_value + 1, range_size)]


def fetch_databricks_table_partitioned(
    table_name: str,
    partition_column: str,
    partition_strategy: str = "value",
    partition_range_size: int | None = None,
    limit: int | None = None,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    if limit is not None:
        return fetch_databricks_table(table_name, limit=limit)

    if partition_strategy == "range":
        ranges = fetch_databricks_partition_ranges(table_name, partition_column, partition_range_size or 20)
        return fetch_databricks_table_by_ranges(table_name, partition_column, ranges)

    partition_values = fetch_databricks_partition_values(table_name, partition_column)
    all_columns: list[str] = []
    all_rows: list[tuple[Any, ...]] = []

    for index, value in enumerate(partition_values, start=1):
        condition = (
            f"{quote_databricks_column(partition_column)} IS NULL"
            if value is None
            else f"{quote_databricks_column(partition_column)} = {sql_literal(value)}"
        )
        log_step(
            f"[replication] Fetching partition {index}/{len(partition_values)} "
            f"for {table_name}: {partition_column}={value}..."
        )
        result = execute_databricks_query(
            f"SELECT * FROM {quote_databricks_identifier(table_name)} WHERE {condition}",
            disposition="EXTERNAL_LINKS",
        )
        if not all_columns:
            all_columns = result.columns
        elif result.columns != all_columns:
            raise RuntimeError(f"Partition column mismatch while fetching {table_name}")
        all_rows.extend(result.rows)

    return all_columns, all_rows


def fetch_databricks_table_by_ranges(
    table_name: str,
    partition_column: str,
    ranges: list[tuple[int, int]],
) -> tuple[list[str], list[tuple[Any, ...]]]:
    all_columns: list[str] = []
    all_rows: list[tuple[Any, ...]] = []

    for index, (start, end) in enumerate(ranges, start=1):
        condition = f"{quote_databricks_column(partition_column)} BETWEEN {start} AND {end}"
        log_step(
            f"[replication] Fetching range partition {index}/{len(ranges)} "
            f"for {table_name}: {partition_column} BETWEEN {start} AND {end}..."
        )
        result = execute_databricks_query(
            f"SELECT * FROM {quote_databricks_identifier(table_name)} WHERE {condition}",
            disposition="EXTERNAL_LINKS",
        )
        if not all_columns:
            all_columns = result.columns
        elif result.columns != all_columns:
            raise RuntimeError(f"Partition column mismatch while fetching {table_name}")
        all_rows.extend(result.rows)

    return all_columns, all_rows


def count_databricks_rows(table_name: str) -> int:
    result = execute_databricks_query(f"SELECT COUNT(*) AS row_count FROM {quote_databricks_identifier(table_name)}")
    if not result.rows:
        return 0
    return int(result.rows[0][0])


def get_greenplum_columns(connection: Any, table_name: str) -> list[str]:
    schema, table = table_name.split(".", 1)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [row[0] for row in cursor.fetchall()]


def count_greenplum_rows(connection: Any, table_name: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {quote_greenplum_identifier(table_name)}")
        return int(cursor.fetchone()[0])


def rows_to_csv(columns: list[str], rows: Iterable[tuple[Any, ...]]) -> io.StringIO:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    buffer.seek(0)
    return buffer


def filter_to_target_columns(
    source_columns: list[str], rows: list[tuple[Any, ...]], target_columns: list[str]
) -> tuple[list[str], list[tuple[Any, ...]]]:
    source_index = {column.lower(): index for index, column in enumerate(source_columns)}
    selected_columns = [column for column in target_columns if column.lower() in source_index]
    selected_rows = [tuple(row[source_index[column.lower()]] for column in selected_columns) for row in rows]
    return selected_columns, selected_rows


def full_refresh_greenplum(connection: Any, table_name: str, columns: list[str], rows: list[tuple[Any, ...]]) -> int:
    if not columns:
        raise ValueError(f"No matching columns found for target table: {table_name}")

    quoted_table = quote_greenplum_identifier(table_name)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    csv_buffer = rows_to_csv(columns, rows)

    with connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {quoted_table}")
        cursor.copy_expert(
            f"COPY {quoted_table} ({quoted_columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)",
            csv_buffer,
        )
    return len(rows)


def create_replication_run(connection: Any) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO dm_meta.replication_runs (status)
            VALUES ('running')
            RETURNING run_id
            """
        )
        return int(cursor.fetchone()[0])


def finish_replication_run(connection: Any, run_id: int, status: str, error_message: str | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE dm_meta.replication_runs
            SET status = %s, finished_at = CURRENT_TIMESTAMP, error_message = %s
            WHERE run_id = %s
            """,
            (status, error_message, run_id),
        )


def insert_table_check(
    connection: Any,
    run_id: int,
    table_name: str,
    databricks_row_count: int | None,
    greenplum_row_count: int | None,
    status: str,
    notes: str | None = None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO dm_meta.replication_table_checks (
                run_id, table_name, databricks_row_count, greenplum_row_count, status, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (run_id, table_name, databricks_row_count, greenplum_row_count, status, notes),
        )


def select_tables(config: ReplicationConfig, table_name: str, run_all: bool, group: str | None) -> tuple[TableMapping, ...]:
    if run_all:
        return config.tables
    if group is not None:
        selected_group = tuple(table for table in config.tables if table.group == group)
        if not selected_group:
            raise ValueError(f"No tables found in replication group: {group}")
        return selected_group
    selected = tuple(
        table for table in config.tables if table.source_table == table_name or table.target_table == table_name
    )
    if not selected:
        raise ValueError(f"Table not found in replication config: {table_name}")
    return selected


def replicate_table(
    greenplum_conn: Any,
    run_id: int,
    table: TableMapping,
    limit: int | None,
) -> dict[str, Any]:
    log_step(f"[replication] Counting Databricks rows for {table.source_table} via REST...")
    databricks_row_count = count_databricks_rows(table.source_table)
    fetch_message = f"up to {limit} rows" if limit is not None else "all rows"
    partition_message = f" partitioned by {table.partition_column}" if table.partition_column and limit is None else ""
    log_step(f"[replication] Fetching {fetch_message} from {table.source_table}{partition_message} via REST...")
    if table.partition_column:
        source_columns, source_rows = fetch_databricks_table_partitioned(
            table.source_table,
            table.partition_column,
            partition_strategy=table.partition_strategy,
            partition_range_size=table.partition_range_size,
            limit=limit,
        )
    else:
        source_columns, source_rows = fetch_databricks_table(table.source_table, limit=limit)
    if limit is None and len(source_rows) != databricks_row_count:
        raise RuntimeError(
            f"Downloaded row count mismatch before loading {table.source_table}: "
            f"expected {databricks_row_count}, got {len(source_rows)}"
        )
    log_step(f"[replication] Reading Greenplum target columns for {table.target_table}...")
    target_columns = get_greenplum_columns(greenplum_conn, table.target_table)
    load_columns, load_rows = filter_to_target_columns(source_columns, source_rows, target_columns)
    log_step(f"[replication] Loading {len(load_rows)} rows into {table.target_table}...")
    full_refresh_greenplum(greenplum_conn, table.target_table, load_columns, load_rows)
    greenplum_row_count = count_greenplum_rows(greenplum_conn, table.target_table)
    status = "limited_load" if limit is not None else ("ok" if databricks_row_count == greenplum_row_count else "mismatch")
    insert_table_check(greenplum_conn, run_id, table.target_table, databricks_row_count, greenplum_row_count, status)
    return {
        "source_table": table.source_table,
        "target_table": table.target_table,
        "databricks_row_count": databricks_row_count,
        "greenplum_row_count": greenplum_row_count,
        "status": status,
        "limit": limit,
        "loaded_columns": load_columns,
    }


def skipped_table_result(greenplum_conn: Any, run_id: int, table: TableMapping, reason: str) -> dict[str, Any]:
    status = "skipped_dependency"
    insert_table_check(greenplum_conn, run_id, table.target_table, None, None, status, reason)
    return {
        "source_table": table.source_table,
        "target_table": table.target_table,
        "databricks_row_count": None,
        "greenplum_row_count": None,
        "status": status,
        "limit": None,
        "loaded_columns": [],
        "error": reason,
    }


def failed_table_result(
    greenplum_conn: Any,
    run_id: int,
    table: TableMapping,
    limit: int | None,
    error: Exception,
) -> dict[str, Any]:
    error_message = str(error)
    insert_table_check(greenplum_conn, run_id, table.target_table, None, None, "failed", error_message)
    return {
        "source_table": table.source_table,
        "target_table": table.target_table,
        "databricks_row_count": None,
        "greenplum_row_count": None,
        "status": "failed",
        "limit": limit,
        "loaded_columns": [],
        "error": error_message,
    }


def final_replication_status(results: list[dict[str, Any]], limit: int | None) -> str:
    if limit is not None:
        if all(result["status"] == "limited_load" for result in results):
            return "test_only"
        if any(result["status"] == "limited_load" for result in results):
            return "partial"
        return "failed"
    if all(result["status"] == "ok" for result in results):
        return "ok"
    if any(result["status"] == "ok" for result in results):
        return "partial"
    return "failed"


def exit_code_for_status(status: str) -> int:
    return {"ok": 0, "partial": 3, "failed": 4, "test_only": 5}.get(status, 4)


def run_databricks_test(table_name: str) -> int:
    missing_databricks = missing_databricks_settings()
    if missing_databricks:
        print("Missing Databricks settings: " + ", ".join(missing_databricks), file=sys.stderr)
        return 2

    log_step(f"[test] Running COUNT(*) for {table_name} via Statement Execution API...")
    row_count = count_databricks_rows(table_name)
    log_step(f"[test] Running LIMIT 5 for {table_name} via Statement Execution API...")
    columns, rows = fetch_databricks_table(table_name, limit=5)

    print(
        json.dumps(
            {
                "table": table_name,
                "row_count": row_count,
                "sample_columns": columns,
                "sample_rows": [list(row) for row in rows],
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
    return 0


def run_replication(config_path: Path, table_name: str, run_all: bool, group: str | None, limit: int | None) -> int:
    config = load_config(config_path)
    missing_databricks = missing_databricks_settings()
    if missing_databricks:
        print("Missing Databricks settings: " + ", ".join(missing_databricks), file=sys.stderr)
        return 2

    missing_greenplum = missing_greenplum_settings()
    if missing_greenplum:
        print("Missing Greenplum settings: " + ", ".join(missing_greenplum), file=sys.stderr)
        return 2

    tables = select_tables(config, table_name, run_all, group)

    dimension_tables = [table for table in tables if table.group == "dimensions"]
    fact_tables = [table for table in tables if table.group == "facts"]
    other_tables = [table for table in tables if table.group not in {"dimensions", "facts"}]

    log_step("[replication] Connecting to Greenplum...")
    with greenplum_connection() as greenplum_conn:
        greenplum_conn.autocommit = False
        log_step("[replication] Creating replication audit run...")
        run_id = create_replication_run(greenplum_conn)
        greenplum_conn.commit()
        results: list[dict[str, Any]] = []
        dimension_failed = False

        if dimension_tables:
            dimension_results: list[dict[str, Any]] = []
            try:
                for table in dimension_tables:
                    dimension_results.append(replicate_table(greenplum_conn, run_id, table, limit))
                greenplum_conn.commit()
                results.extend(dimension_results)
            except Exception as error:
                greenplum_conn.rollback()
                dimension_failed = True
                failed_table = dimension_tables[len(dimension_results)]
                log_step(f"[replication] Failed dimension batch at {failed_table.target_table}: {error}")
                results.append(failed_table_result(greenplum_conn, run_id, failed_table, limit, error))
                remaining_dimensions = dimension_tables[len(dimension_results) + 1 :]
                for table in remaining_dimensions:
                    reason = "Skipped because dimension batch failed before this table"
                    results.append(skipped_table_result(greenplum_conn, run_id, table, reason))
                greenplum_conn.commit()

        for table in other_tables:
            try:
                results.append(replicate_table(greenplum_conn, run_id, table, limit))
                greenplum_conn.commit()
            except Exception as error:
                greenplum_conn.rollback()
                log_step(f"[replication] Failed {table.target_table}: {error}")
                results.append(failed_table_result(greenplum_conn, run_id, table, limit, error))
                greenplum_conn.commit()

        for table in fact_tables:
            if dimension_tables and dimension_failed:
                reason = "Skipped because one or more dimensions failed in this replication run"
                log_step(f"[replication] Skipping {table.target_table}: {reason}")
                results.append(skipped_table_result(greenplum_conn, run_id, table, reason))
                greenplum_conn.commit()
                continue
            try:
                results.append(replicate_table(greenplum_conn, run_id, table, limit))
                greenplum_conn.commit()
            except Exception as error:
                greenplum_conn.rollback()
                log_step(f"[replication] Failed {table.target_table}: {error}")
                results.append(failed_table_result(greenplum_conn, run_id, table, limit, error))
                greenplum_conn.commit()

        final_status = final_replication_status(results, limit)
        finish_replication_run(greenplum_conn, run_id, final_status)
        greenplum_conn.commit()

    print(json.dumps({"run_id": run_id, "status": final_status, "results": results}, indent=2, ensure_ascii=False))
    return exit_code_for_status(final_status)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Databricks-to-Greenplum replication runner")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Source or target table to replicate")
    parser.add_argument("--group", choices=("dimensions", "facts"), help="Replicate a configured group of tables")
    parser.add_argument("--all", action="store_true", help="Replicate every table in the manifest")
    parser.add_argument("--limit", type=int, help="Load only N rows for connectivity testing")
    parser.add_argument("--test-databricks", action="store_true", help="Test Databricks COUNT and LIMIT queries only")
    parser.add_argument("--preflight", action="store_true", help="Show configuration readiness without running replication")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.preflight:
        return run_preflight(args.config)
    if args.test_databricks:
        return run_databricks_test(args.table)
    return run_replication(args.config, args.table, args.all, args.group, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
