#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${GREENPLUM_BACKUP_DIR:-$(pwd)/backups/greenplum}"
GREENPLUM_HOST="${GREENPLUM_HOST:-localhost}"
GREENPLUM_PORT="${GREENPLUM_PORT:-5432}"
GREENPLUM_DB="${GREENPLUM_DB:-dw_semis2}"
GREENPLUM_USER="${GREENPLUM_USER:-gpadmin}"
GREENPLUM_CONTAINER="${GREENPLUM_CONTAINER:-dw-greenplum}"
GREENPLUM_CONTAINER_PG_DUMP="${GREENPLUM_CONTAINER_PG_DUMP:-/usr/local/greenplum-db/bin/pg_dump}"
RETENTION_DAYS="${GREENPLUM_BACKUP_RETENTION_DAYS:-7}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="${BACKUP_DIR}/${GREENPLUM_DB}_${timestamp}.dump"

mkdir -p "${BACKUP_DIR}"

if command -v pg_dump >/dev/null 2>&1; then
  pg_dump \
    -Fc \
    -h "${GREENPLUM_HOST}" \
    -p "${GREENPLUM_PORT}" \
    -U "${GREENPLUM_USER}" \
    "${GREENPLUM_DB}" \
    > "${backup_file}"
else
  if ! docker exec "${GREENPLUM_CONTAINER}" test -x "${GREENPLUM_CONTAINER_PG_DUMP}"; then
    printf 'pg_dump not found on host or container path: %s\n' "${GREENPLUM_CONTAINER_PG_DUMP}" >&2
    exit 127
  fi

  docker exec \
    -e PGPASSWORD="${PGPASSWORD:-}" \
    "${GREENPLUM_CONTAINER}" \
    "${GREENPLUM_CONTAINER_PG_DUMP}" \
      -Fc \
      -h localhost \
      -p 5432 \
      -U "${GREENPLUM_USER}" \
      "${GREENPLUM_DB}" \
    > "${backup_file}"
fi

gzip -f "${backup_file}"

find "${BACKUP_DIR}" -name "${GREENPLUM_DB}_*.dump.gz" -type f -mtime "+${RETENTION_DAYS}" -delete

printf 'Greenplum backup created: %s.gz\n' "${backup_file}"
