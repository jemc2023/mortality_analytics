from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from replicate import (
    execute_databricks_query,
    greenplum_connection,
    missing_databricks_settings,
    missing_greenplum_settings,
    quote_databricks_identifier,
)


DEFAULT_PIPELINE_RUNS_TABLE = "workspace.dm_meta.pipeline_runs"
DEFAULT_PIPELINE_NAME = "mortality_etl_pipeline"
STALE_RUNNING_MINUTES = int(os.getenv("GREENPLUM_STALE_RUNNING_MINUTES", "120"))
DW_DIR = Path(__file__).resolve().parents[1]
TERMINAL_STATUSES = {"replicated", "partial", "failed"}
REPLICATION_EXIT_STATUS = {
    0: "replicated",
    3: "partial",
    4: "failed",
    5: "test_only",
}


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    pipeline_name: str
    status: str
    completed_at: str | None
    source: str | None
    notes: str | None


def log_step(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def ensure_processed_table(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dm_meta.processed_pipeline_runs (
                run_id VARCHAR(255) NOT NULL,
                pipeline_name VARCHAR(255) NOT NULL,
                databricks_completed_at TIMESTAMP,
                replication_status VARCHAR(32) NOT NULL,
                first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_attempt_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                replicated_at TIMESTAMP,
                attempt_count INT NOT NULL DEFAULT 0,
                error_message TEXT,
                notes TEXT,
                PRIMARY KEY (run_id)
            )
            DISTRIBUTED BY (run_id)
            """
        )


def latest_successful_pipeline_run(table_name: str, pipeline_name: str | None) -> PipelineRun | None:
    where_clauses = ["status = 'SUCCESS'"]
    if pipeline_name:
        safe_pipeline = pipeline_name.replace("'", "''")
        where_clauses.append(f"pipeline_name = '{safe_pipeline}'")

    query = f"""
        SELECT run_id, pipeline_name, status, completed_at, source, notes
        FROM {quote_databricks_identifier(table_name)}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY completed_at DESC
        LIMIT 1
    """
    result = execute_databricks_query(query)
    if not result.rows:
        return None

    run_id, name, status, completed_at, source, notes = result.rows[0]
    return PipelineRun(
        run_id=str(run_id),
        pipeline_name=str(name),
        status=str(status),
        completed_at=str(completed_at) if completed_at is not None else None,
        source=str(source) if source is not None else None,
        notes=str(notes) if notes is not None else None,
    )


def processed_status(connection: Any, run_id: str) -> str | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CASE
                WHEN replication_status = 'running'
                 AND last_attempt_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 minute')
                THEN 'retry_requested'
                ELSE replication_status
            END
            FROM dm_meta.processed_pipeline_runs
            WHERE run_id = %s
            """,
            (STALE_RUNNING_MINUTES, run_id),
        )
        row = cursor.fetchone()
        return str(row[0]) if row else None


def lock_processed_runs(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute("LOCK TABLE dm_meta.processed_pipeline_runs IN EXCLUSIVE MODE")


def mark_attempt_started(connection: Any, pipeline_run: PipelineRun) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE dm_meta.processed_pipeline_runs
            SET replication_status = 'running',
                last_attempt_at = CURRENT_TIMESTAMP,
                attempt_count = attempt_count + 1,
                error_message = NULL
            WHERE run_id = %s
            """,
            (pipeline_run.run_id,),
        )
        if cursor.rowcount:
            return

        cursor.execute(
            """
            INSERT INTO dm_meta.processed_pipeline_runs (
                run_id, pipeline_name, databricks_completed_at, replication_status,
                attempt_count, notes
            )
            VALUES (%s, %s, %s, 'running', 1, %s)
            """,
            (pipeline_run.run_id, pipeline_run.pipeline_name, pipeline_run.completed_at, pipeline_run.notes),
        )


def mark_attempt_finished(connection: Any, run_id: str, status: str, error_message: str | None = None) -> None:
    replicated_at_expression = "CURRENT_TIMESTAMP" if status == "replicated" else "replicated_at"
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE dm_meta.processed_pipeline_runs
            SET replication_status = %s,
                last_attempt_at = CURRENT_TIMESTAMP,
                replicated_at = {replicated_at_expression},
                error_message = %s
            WHERE run_id = %s
            """,
            (status, error_message, run_id),
        )


def run_replication(make_target: str, dry_run: bool) -> int:
    command = replication_command(make_target)
    if dry_run:
        log_step(f"[pipeline-check] Dry run: would execute {' '.join(command)} in {DW_DIR}")
        return 0

    log_step(f"[pipeline-check] Executing {' '.join(command)} in {DW_DIR}...")
    completed = subprocess.run(command, cwd=DW_DIR, check=False)
    return int(completed.returncode)


def replication_command(make_target: str) -> list[str]:
    target_args = {
        "replicate-all": ["--all"],
        "replicate-all-limit": ["--all", "--limit", "100"],
        "replicate-dimensions": ["--group", "dimensions"],
        "replicate-dimensions-limit": ["--group", "dimensions", "--limit", "100"],
        "replicate-facts": ["--group", "facts"],
        "replicate-facts-limit": ["--group", "facts", "--limit", "100"],
        "replicate-dim-genero": ["--table", "workspace.dm_mortality.dim_genero"],
        "replicate-dim-genero-limit": ["--table", "workspace.dm_mortality.dim_genero", "--limit", "100"],
        "replicate-dim-tiempo": ["--table", "workspace.dm_mortality.dim_tiempo"],
        "replicate-dim-tiempo-limit": ["--table", "workspace.dm_mortality.dim_tiempo", "--limit", "100"],
    }
    if make_target not in target_args:
        return ["make", make_target]
    return [sys.executable, "replication/replicate.py", *target_args[make_target]]


def is_limited_make_target(make_target: str) -> bool:
    return make_target.endswith("-limit") or "limit" in make_target


def validate_environment() -> list[str]:
    return missing_databricks_settings() + missing_greenplum_settings()


def check_and_replicate(args: argparse.Namespace) -> int:
    missing = validate_environment()
    if missing:
        print("Missing settings: " + ", ".join(missing), file=sys.stderr)
        return 2

    log_step(f"[pipeline-check] Reading latest SUCCESS from {args.pipeline_runs_table}...")
    pipeline_run = latest_successful_pipeline_run(args.pipeline_runs_table, args.pipeline_name)
    if pipeline_run is None:
        print(json.dumps({"status": "no_successful_pipeline_run"}, indent=2))
        return 0

    with greenplum_connection() as connection:
        connection.autocommit = False
        ensure_processed_table(connection)
        lock_processed_runs(connection)
        status = processed_status(connection, pipeline_run.run_id)

        if status in TERMINAL_STATUSES or (status == "test_only" and is_limited_make_target(args.make_target)):
            connection.commit()
            print(
                json.dumps(
                    {
                        "status": f"already_{status}",
                        "pipeline_run": pipeline_run.__dict__,
                        "current_greenplum_status": status,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        if status == "running":
            connection.commit()
            print(
                json.dumps(
                    {"status": "replication_already_running", "pipeline_run": pipeline_run.__dict__},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        if args.dry_run:
            connection.commit()
            print(
                json.dumps(
                    {
                        "status": "would_replicate",
                        "pipeline_run": pipeline_run.__dict__,
                        "current_greenplum_status": status,
                        "make_target": args.make_target,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        mark_attempt_started(connection, pipeline_run)
        connection.commit()

        replication_code = run_replication(args.make_target, args.dry_run)
        final_status = REPLICATION_EXIT_STATUS.get(replication_code, "failed")
        error_message = None if replication_code == 0 else f"Replication command exited with code {replication_code}"

        mark_attempt_finished(connection, pipeline_run.run_id, final_status, error_message)
        connection.commit()

    print(
        json.dumps(
            {
                "status": final_status,
                "pipeline_run": pipeline_run.__dict__,
                "make_target": args.make_target,
                "dry_run": args.dry_run,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return replication_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Greenplum replication only after a new Databricks pipeline run")
    parser.add_argument(
        "--pipeline-runs-table",
        default=os.getenv("DATABRICKS_PIPELINE_RUNS_TABLE", DEFAULT_PIPELINE_RUNS_TABLE),
        help="Databricks control table containing pipeline run completions",
    )
    parser.add_argument(
        "--pipeline-name",
        default=os.getenv("DATABRICKS_PIPELINE_NAME", DEFAULT_PIPELINE_NAME),
        help="Pipeline name to filter; use an empty string to accept any pipeline",
    )
    parser.add_argument(
        "--make-target",
        default=os.getenv("GREENPLUM_REPLICATION_MAKE_TARGET", "replicate-all"),
        help="Make target to execute when a new successful pipeline run is found",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show whether replication would run without changing state")
    args = parser.parse_args()
    if args.pipeline_name == "":
        args.pipeline_name = None
    return args


def main() -> int:
    return check_and_replicate(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
