#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE=".env.local"
API_URL="http://localhost:8080"
ADMIN_KEY="${BOOTSTRAP_ADMIN_KEY:-dev-bootstrap-key}"
REPORT_DIR="${ROOT_DIR}/reports/phase1a-local"
SUMMARY_FILE="${REPORT_DIR}/summary.md"
JUNIT_FILE="${REPORT_DIR}/junit.xml"
EXIT_FILE="${REPORT_DIR}/exit_code.txt"

echo "[phase1a] Starting Docker Compose stack"
docker compose --env-file "${ENV_FILE}" up -d --build

echo "[phase1a] Waiting for /health"
for _ in $(seq 1 60); do
  code="$(curl -s -o /tmp/phase1a_health.out -w "%{http_code}" "${API_URL}/health" || true)"
  if [[ "${code}" == "200" ]]; then
    break
  fi
  sleep 2
done

export SERVICE_URL="${API_URL}"
export REPORT_DIR
export REPORT_BRANCH="local"
export BUILD_ID="manual-local"
export POST_DEPLOY_ADMIN_KEY="${ADMIN_KEY}"
export FUNCTIONAL_BEARER_TOKEN="dev-local-token"
export SUMMARY_FILE
export JUNIT_FILE
export EXIT_FILE
export SUITE_TITLE="Phase 1A Local Functional Test Summary"
export SCENARIOS="uc_1a_001_tenant_onboarding uc_1a_002_customer_site_flow uc_1a_003_tech_submit_validation"

bash "${ROOT_DIR}/scripts/functional/run_functional_suite.sh"

if [[ "$(cat "${EXIT_FILE}")" != "0" ]]; then
  echo "[phase1a] FAILED: see ${SUMMARY_FILE}"
  exit 1
fi

echo "[phase1a] PASSED: functional suite is green"
echo "[phase1a] Reports:"
echo "- ${SUMMARY_FILE}"
echo "- ${JUNIT_FILE}"
echo "- ${EXIT_FILE}"
