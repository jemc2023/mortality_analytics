#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_PREFIX="[greenplum-pipeline-check]"
LOCK_DIR="/tmp/greenplum_pipeline_check.lock"

timestamp() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  printf '%s another checker is already running, skipping at %s\n' "${LOG_PREFIX}" "$(timestamp)"
  exit 0
fi
trap 'rmdir "${LOCK_DIR}"' EXIT

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
python3 replication/check_pipeline_runs.py "$@"

printf '%s finished at %s\n' "${LOG_PREFIX}" "$(timestamp)"
