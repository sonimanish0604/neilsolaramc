#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE="${ENV_FILE:-.env.local}"
REPORT_DIR="${ROOT_DIR}/reports/phase1e-local"
SUMMARY_FILE="${REPORT_DIR}/summary.md"
JUNIT_FILE="${REPORT_DIR}/junit.xml"
EXIT_FILE="${REPORT_DIR}/exit_code.txt"
PYTEST_LOG="${REPORT_DIR}/pytest_output.txt"

PHASE1E_PYTEST_TARGETS="${PHASE1E_PYTEST_TARGETS:-tests/test_phase1e_geo_validation.py tests/test_phase1d_generation_rules.py tests/test_phase1a_validations.py}"

mkdir -p "${REPORT_DIR}"

echo "[phase1e] Starting Docker Compose stack (postgres + api)"
docker compose --env-file "${ENV_FILE}" up -d --build postgres api

echo "[phase1e] Running targeted pytest suite in API container"
pytest_exit=0
if ! docker compose --env-file "${ENV_FILE}" run --rm \
  -v "${ROOT_DIR}/backend:/app" \
  -v "${REPORT_DIR}:/reports" \
  api bash -lc '
  set -euo pipefail
  cd /app
  if ! python -c "import pytest" >/dev/null 2>&1; then
    python -m pip install --no-cache-dir pytest
  fi
  PYTHONPATH=/app alembic upgrade head
  PYTHONPATH=/app python -m pytest -q -o cache_dir=/tmp/pytest_cache '"${PHASE1E_PYTEST_TARGETS}"' --junitxml=/reports/junit.xml
' | tee "${PYTEST_LOG}"; then
  pytest_exit=1
fi

if [[ ! -f "${JUNIT_FILE}" ]]; then
  cat > "${JUNIT_FILE}" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="phase1e_pytest" tests="1" failures="1" skipped="0">
  <testcase classname="phase1e" name="pytest_suite">
    <failure message="pytest execution failed before junit generation"/>
  </testcase>
</testsuite>
XML
fi

echo "${pytest_exit}" > "${EXIT_FILE}"

{
  echo "# Phase 1E Local Validation Summary"
  echo
  echo "- Timestamp: \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
  echo "- Pytest exit: \`${pytest_exit}\`"
  echo
  echo "## Artifacts"
  echo "- \`${PYTEST_LOG}\`"
  echo "- \`${JUNIT_FILE}\`"
  echo "- \`${EXIT_FILE}\`"
} > "${SUMMARY_FILE}"

cat "${SUMMARY_FILE}"

if [[ "${pytest_exit}" != "0" ]]; then
  echo "[phase1e] FAILED"
  exit 1
fi

echo "[phase1e] PASSED"
