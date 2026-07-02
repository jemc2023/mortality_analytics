#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_PREFIX="[greenplum-replication]"

timestamp() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

cd "${REPO_ROOT}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

printf '%s started at %s\n' "${LOG_PREFIX}" "$(timestamp)"

cd "${SCRIPT_DIR}"
make replicate-all

printf '%s finished at %s\n' "${LOG_PREFIX}" "$(timestamp)"
