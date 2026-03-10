#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE="${ENV_FILE:-.env.local}"
API_URL="${API_URL:-http://localhost:8080}"
ADMIN_KEY="${BOOTSTRAP_ADMIN_KEY:-dev-bootstrap-key}"
REPORT_DIR="${ROOT_DIR}/reports/phase1b-local"
FUNC_REPORT_DIR="${REPORT_DIR}/functional"
PYTEST_LOG="${REPORT_DIR}/pytest_output.txt"
PYTEST_JUNIT="${REPORT_DIR}/pytest_junit.xml"
PYTEST_EXIT_FILE="${REPORT_DIR}/pytest_exit_code.txt"
FUNC_SUMMARY_FILE="${FUNC_REPORT_DIR}/summary.md"
FUNC_JUNIT_FILE="${FUNC_REPORT_DIR}/junit.xml"
FUNC_EXIT_FILE="${FUNC_REPORT_DIR}/exit_code.txt"
OVERALL_SUMMARY_FILE="${REPORT_DIR}/summary.md"

PHASE1B_PYTEST_TARGETS="${PHASE1B_PYTEST_TARGETS:-tests/test_phase1b_services.py tests/test_report_generation.py tests/test_notification_engine_skeleton.py tests/test_notification_events.py tests/test_notification_runtime.py tests/test_notification_maintenance.py tests/test_email_adapter_routing.py tests/test_mailgun_adapter.py tests/test_secret_resolver.py}"
RUN_PHASE1B_PYTEST="${RUN_PHASE1B_PYTEST:-true}"

mkdir -p "${REPORT_DIR}" "${FUNC_REPORT_DIR}"

echo "[phase1b] Starting Docker Compose stack"
docker compose --env-file "${ENV_FILE}" up -d --build

echo "[phase1b] Waiting for /health"
for _ in $(seq 1 60); do
  code="$(curl -s -o /tmp/phase1b_health.out -w "%{http_code}" "${API_URL}/health" || true)"
  if [[ "${code}" == "200" ]]; then
    break
  fi
  sleep 2
done

code="$(curl -s -o /tmp/phase1b_health.out -w "%{http_code}" "${API_URL}/health" || true)"
if [[ "${code}" != "200" ]]; then
  echo "[phase1b] health check failed with HTTP ${code}"
  cat /tmp/phase1b_health.out || true
  exit 1
fi

pytest_exit=0
if [[ "${RUN_PHASE1B_PYTEST}" == "true" ]]; then
  echo "[phase1b] Running targeted pytest suite in API container"
  if ! docker compose --env-file "${ENV_FILE}" run --rm \
    -v "${ROOT_DIR}/backend:/workspace-backend:ro" \
    -v "${REPORT_DIR}:/reports" \
    api bash -lc '
    set -euo pipefail
    cd /workspace-backend
    if ! python -c "import pytest" >/dev/null 2>&1; then
      python -m pip install --no-cache-dir pytest
    fi
    PYTHONPATH=/app python -m pytest -q -o cache_dir=/tmp/pytest_cache '"${PHASE1B_PYTEST_TARGETS}"' --junitxml=/reports/pytest_junit.xml
  ' | tee "${PYTEST_LOG}"; then
    pytest_exit=1
  fi
else
  echo "[phase1b] Skipping pytest because RUN_PHASE1B_PYTEST=false"
  echo "SKIPPED (RUN_PHASE1B_PYTEST=false)" > "${PYTEST_LOG}"
  cat > "${PYTEST_JUNIT}" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="phase1b_pytest" tests="1" failures="0" skipped="1">
  <testcase classname="phase1b" name="pytest_suite">
    <skipped message="RUN_PHASE1B_PYTEST=false"/>
  </testcase>
</testsuite>
XML
fi
echo "${pytest_exit}" > "${PYTEST_EXIT_FILE}"

if [[ ! -f "${PYTEST_JUNIT}" ]]; then
  if [[ "${pytest_exit}" == "0" ]]; then
    cat > "${PYTEST_JUNIT}" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="phase1b_pytest" tests="0" failures="0" skipped="0"/>
XML
  else
    cat > "${PYTEST_JUNIT}" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="phase1b_pytest" tests="1" failures="1" skipped="0">
  <testcase classname="phase1b" name="pytest_suite">
    <failure message="pytest execution failed before junit generation"/>
  </testcase>
</testsuite>
XML
  fi
fi

echo "[phase1b] Running functional scenarios"
export SERVICE_URL="${API_URL}"
export REPORT_DIR="${FUNC_REPORT_DIR}"
export REPORT_BRANCH="local"
export BUILD_ID="manual-local-phase1b"
export POST_DEPLOY_ADMIN_KEY="${ADMIN_KEY}"
export FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-dev-local-token}"
export FUNCTIONAL_APPROVAL_TOKEN="${FUNCTIONAL_APPROVAL_TOKEN:-}"
export FUNCTIONAL_CUSTOMER_SIGNER_NAME="${FUNCTIONAL_CUSTOMER_SIGNER_NAME:-}"
export FUNCTIONAL_CUSTOMER_SIGNER_PHONE="${FUNCTIONAL_CUSTOMER_SIGNER_PHONE:-}"
export FUNCTIONAL_CUSTOMER_SIGNATURE_OBJECT_PATH="${FUNCTIONAL_CUSTOMER_SIGNATURE_OBJECT_PATH:-}"
export FUNCTIONAL_PHASE1B_EMAIL_TO="${FUNCTIONAL_PHASE1B_EMAIL_TO:-}"
export FUNCTIONAL_PHASE1B_DOMAIN_SELECTOR="${FUNCTIONAL_PHASE1B_DOMAIN_SELECTOR:-1}"
export FUNCTIONAL_PHASE1B_EMAIL_FROM="${FUNCTIONAL_PHASE1B_EMAIL_FROM:-}"
export FUNCTIONAL_PHASE1B_EMAIL_SUBJECT="${FUNCTIONAL_PHASE1B_EMAIL_SUBJECT:-}"
export FUNCTIONAL_PHASE1B_EMAIL_TEXT="${FUNCTIONAL_PHASE1B_EMAIL_TEXT:-}"
export SUMMARY_FILE="${FUNC_SUMMARY_FILE}"
export JUNIT_FILE="${FUNC_JUNIT_FILE}"
export EXIT_FILE="${FUNC_EXIT_FILE}"
export SUITE_TITLE="Phase 1B Local Functional Test Summary"
export SCENARIOS="uc_1b_001_approval_token_flow uc_1b_002_notification_email_smoke"

bash "${ROOT_DIR}/scripts/functional/run_functional_suite.sh" || true

func_exit=1
if [[ -f "${FUNC_EXIT_FILE}" ]]; then
  func_exit="$(cat "${FUNC_EXIT_FILE}")"
fi

overall_exit=0
if [[ "${pytest_exit}" != "0" || "${func_exit}" != "0" ]]; then
  overall_exit=1
fi

{
  echo "# Phase 1B Local Validation Summary"
  echo
  echo "- API URL: \`${API_URL}\`"
  echo "- Timestamp: \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
  echo "- Pytest exit: \`${pytest_exit}\`"
  echo "- Functional exit: \`${func_exit}\`"
  echo "- Overall exit: \`${overall_exit}\`"
  echo
  echo "## Artifacts"
  echo "- \`${PYTEST_LOG}\`"
  echo "- \`${PYTEST_JUNIT}\`"
  echo "- \`${PYTEST_EXIT_FILE}\`"
  echo "- \`${FUNC_SUMMARY_FILE}\`"
  echo "- \`${FUNC_JUNIT_FILE}\`"
  echo "- \`${FUNC_EXIT_FILE}\`"
} > "${OVERALL_SUMMARY_FILE}"

cat "${OVERALL_SUMMARY_FILE}"

if [[ "${overall_exit}" != "0" ]]; then
  echo "[phase1b] FAILED"
  exit 1
fi

echo "[phase1b] PASSED"
