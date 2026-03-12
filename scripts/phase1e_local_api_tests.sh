#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"

ENV_FILE="${ENV_FILE:-.env.local}"
SERVICE_URL="${SERVICE_URL:-http://localhost:8080}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-dev-local-token}"
FUNCTIONAL_ASSIGNED_TECH_USER_ID="${FUNCTIONAL_ASSIGNED_TECH_USER_ID:-}"
REPORT_DIR="${ROOT_DIR}/reports/phase1e-local"
SUMMARY_FILE="${REPORT_DIR}/summary.md"
JUNIT_FILE="${REPORT_DIR}/junit.xml"
EXIT_FILE="${REPORT_DIR}/exit_code.txt"
REPORT_BRANCH="${REPORT_BRANCH:-local}"
BUILD_ID="${BUILD_ID:-manual-local}"

mkdir -p "${REPORT_DIR}"
# Remove stale artifacts (including root-owned files from prior container writes)
find "${REPORT_DIR}" -mindepth 1 -maxdepth 1 -type f -delete 2>/dev/null || true

resolve_local_dev_user_id() {
  local container_name="${POSTGRES_CONTAINER_NAME:-neilsolar-postgres-local}"
  local db_name="${POSTGRES_DB:-neilsolar_local}"
  local db_user="${POSTGRES_USER:-postgres}"
  local user_id
  user_id="$(docker exec "${container_name}" psql -U "${db_user}" -d "${db_name}" -t -A -c "select id::text from users where firebase_uid='local-dev-user' limit 1;" 2>/dev/null | tr -d '\r\n' || true)"
  echo "${user_id}"
}

echo "[phase1e] Starting Docker Compose stack (postgres + api)"
docker compose --env-file "${ENV_FILE}" up -d --build postgres api

echo "[phase1e] Waiting for /health"
health_code="000"
for _ in $(seq 1 60); do
  health_code="$(curl -s -o "${REPORT_DIR}/health.out" -w "%{http_code}" "${SERVICE_URL}/health" || true)"
  if [[ "${health_code}" == "200" ]]; then
    break
  fi
  sleep 2
done
run_test "preflight health endpoint" "200" "${health_code}"

if [[ "${health_code}" != "200" ]]; then
  write_reports \
    "Phase 1E Local API Test Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH}" \
    "${BUILD_ID}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  cat "${SUMMARY_FILE}"
  exit 1
fi

if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  FUNCTIONAL_ASSIGNED_TECH_USER_ID="$(resolve_local_dev_user_id)"
fi
if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  run_test "resolve local-dev-user id" "NON_EMPTY" "EMPTY"
  write_reports \
    "Phase 1E Local API Test Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH}" \
    "${BUILD_ID}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  cat "${SUMMARY_FILE}"
  echo "[phase1e] Unable to resolve local-dev-user ID from postgres."
  echo "[phase1e] Set FUNCTIONAL_ASSIGNED_TECH_USER_ID explicitly and re-run."
  exit 1
fi

echo "[phase1e] Running Phase 1E functional scenarios"
export SERVICE_URL
export REPORT_DIR
export REPORT_BRANCH
export BUILD_ID
export FUNCTIONAL_BEARER_TOKEN
export FUNCTIONAL_ASSIGNED_TECH_USER_ID
export SUMMARY_FILE
export JUNIT_FILE
export EXIT_FILE

bash "${ROOT_DIR}/scripts/phase1e_post_deploy_tests.sh"

cat "${SUMMARY_FILE}"
if [[ ! -f "${EXIT_FILE}" || "$(cat "${EXIT_FILE}")" != "0" ]]; then
  echo "[phase1e] FAILED"
  exit 1
fi

echo "[phase1e] PASSED"
echo "[phase1e] Reports:"
echo "- ${SUMMARY_FILE}"
echo "- ${JUNIT_FILE}"
echo "- ${EXIT_FILE}"
