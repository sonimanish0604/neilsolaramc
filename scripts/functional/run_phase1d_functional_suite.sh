#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"
source "${ROOT_DIR}/scripts/functional/scenarios/uc_1d_001_setup_site_inventory.sh"
source "${ROOT_DIR}/scripts/functional/scenarios/uc_1d_002_visit1_capture_baseline.sh"
source "${ROOT_DIR}/scripts/functional/scenarios/uc_1d_003_visit2_capture_delta.sh"

SERVICE_URL="${SERVICE_URL:-http://localhost:8080}"
REPORT_DIR="${REPORT_DIR:-${ROOT_DIR}/reports/phase1d-local/functional}"
REPORT_BRANCH="${REPORT_BRANCH:-local}"
BUILD_ID="${BUILD_ID:-manual-local}"
ADMIN_KEY="${POST_DEPLOY_ADMIN_KEY:-${BOOTSTRAP_ADMIN_KEY:-dev-bootstrap-key}}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-dev-local-token}"
FUNCTIONAL_ASSIGNED_TECH_USER_ID="${FUNCTIONAL_ASSIGNED_TECH_USER_ID:-}"
P1D_VISIT1_SCHEDULED_AT="${P1D_VISIT1_SCHEDULED_AT:-2026-01-05T10:00:00Z}"
P1D_VISIT2_SCHEDULED_AT="${P1D_VISIT2_SCHEDULED_AT:-2026-01-15T10:00:00Z}"
SCENARIOS="${SCENARIOS:-uc_1d_001_setup_site_inventory uc_1d_002_visit1_capture_baseline uc_1d_003_visit2_capture_delta}"

SUMMARY_FILE="${SUMMARY_FILE:-${REPORT_DIR}/summary.md}"
JUNIT_FILE="${JUNIT_FILE:-${REPORT_DIR}/junit.xml}"
EXIT_FILE="${EXIT_FILE:-${REPORT_DIR}/exit_code.txt}"
SUITE_TITLE="${SUITE_TITLE:-Phase 1D Functional API Capture Summary}"

P1D_SETUP_OK="false"
P1D_CUSTOMER_ID=""
P1D_SITE_ID=""
P1D_INV1_ID=""
P1D_INV2_ID=""
P1D_WO1_ID=""

mkdir -p "${REPORT_DIR}"

json_path() {
  local path="$1"
  local file="$2"
  python3 - "$path" "$file" <<'PY'
import json
import sys

path, file_path = sys.argv[1], sys.argv[2]
try:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print("")
    raise SystemExit(0)

cur = data
for part in path.split('.'):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
        continue
    if isinstance(cur, list):
        try:
            idx = int(part)
        except Exception:
            print("")
            raise SystemExit(0)
        if idx < 0 or idx >= len(cur):
            print("")
            raise SystemExit(0)
        cur = cur[idx]
        continue
    print("")
    raise SystemExit(0)

if cur is None:
    print("")
else:
    print(cur)
PY
}

api_call() {
  local method="$1"
  local url="$2"
  local payload="$3"
  local out_file="$4"
  http_code "${method}" "${url}" "${payload}" "${out_file}" "false" "${FUNCTIONAL_BEARER_TOKEN}"
}

resolve_local_dev_user_id() {
  local container_name="${POSTGRES_CONTAINER_NAME:-neilsolar-postgres-local}"
  local db_name="${POSTGRES_DB:-neilsolar_local}"
  local db_user="${POSTGRES_USER:-postgres}"
  local user_id
  user_id="$(docker exec "${container_name}" psql -U "${db_user}" -d "${db_name}" -t -A -c "select id::text from users where firebase_uid='local-dev-user' limit 1;" 2>/dev/null | tr -d '\r\n' || true)"
  echo "${user_id}"
}

run_preflight_checks() {
  local health_code
  health_code="000"
  for _ in $(seq 1 60); do
    health_code="$(http_code GET "${SERVICE_URL}/health" "" "${REPORT_DIR}/preflight_health.out")"
    if [[ "|200|401|403|" == *"|${health_code}|"* ]]; then
      break
    fi
    sleep 1
  done
  run_test "preflight health endpoint" "200|401|403" "${health_code}"
  [[ "|200|401|403|" == *"|${health_code}|"* ]]
}

run_selected_scenarios() {
  local scenario
  for scenario in ${SCENARIOS}; do
    case "${scenario}" in
      uc_1d_001_setup_site_inventory)
        scenario_uc_1d_001_setup_site_inventory
        ;;
      uc_1d_002_visit1_capture_baseline)
        scenario_uc_1d_002_visit1_capture_baseline
        ;;
      uc_1d_003_visit2_capture_delta)
        scenario_uc_1d_003_visit2_capture_delta
        ;;
      *)
        run_skip "scenario ${scenario}" "Unknown scenario"
        ;;
    esac
  done
}

if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  FUNCTIONAL_ASSIGNED_TECH_USER_ID="$(resolve_local_dev_user_id)"
fi

if [[ -z "${FUNCTIONAL_BEARER_TOKEN}" ]]; then
  run_skip "precondition bearer token configured" "FUNCTIONAL_BEARER_TOKEN is empty"
else
  if run_preflight_checks; then
    run_selected_scenarios
  else
    run_skip "phase1d scenarios execution" "Preflight health check failed"
  fi
fi

write_reports \
  "${SUITE_TITLE}" \
  "${SERVICE_URL}" \
  "${REPORT_BRANCH}" \
  "${BUILD_ID}" \
  "${SUMMARY_FILE}" \
  "${JUNIT_FILE}" \
  "${EXIT_FILE}"

cat "${SUMMARY_FILE}"
if [[ "$(cat "${EXIT_FILE}")" != "0" ]]; then
  exit 1
fi
