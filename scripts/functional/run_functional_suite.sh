#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

SERVICE_URL="${SERVICE_URL:?SERVICE_URL is required}"
REPORT_DIR="${REPORT_DIR:-/workspace/reports}"
REPORT_BRANCH="${REPORT_BRANCH:-manual}"
BUILD_ID="${BUILD_ID:-manual}"
ADMIN_KEY="${POST_DEPLOY_ADMIN_KEY:-${BOOTSTRAP_ADMIN_KEY:-dev-bootstrap-key}}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-}"

SUMMARY_FILE="${SUMMARY_FILE:-${REPORT_DIR}/functional_summary.md}"
JUNIT_FILE="${JUNIT_FILE:-${REPORT_DIR}/functional_junit.xml}"
EXIT_FILE="${EXIT_FILE:-${REPORT_DIR}/functional_exit_code.txt}"
SUITE_TITLE="${SUITE_TITLE:-Functional Use Case Test Summary}"
SCENARIOS="${SCENARIOS:-uc_1a_001_tenant_onboarding uc_1a_002_customer_site_flow uc_1a_003_tech_submit_validation}"

mkdir -p "${REPORT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"
source "${ROOT_DIR}/scripts/functional/scenarios/uc_1a_001_tenant_onboarding.sh"
source "${ROOT_DIR}/scripts/functional/scenarios/uc_1a_002_customer_site_flow.sh"
source "${ROOT_DIR}/scripts/functional/scenarios/uc_1a_003_tech_submit_validation.sh"

run_preflight_checks() {
  local health_code
  health_code="$(http_code GET "${SERVICE_URL}/health" "" "${REPORT_DIR}/preflight_health.out")"
  run_test "preflight health endpoint" "200|401|403" "${health_code}"

  local ready_code
  ready_code="$(http_code GET "${SERVICE_URL}/ready" "" "${REPORT_DIR}/preflight_ready.out")"
  run_test "preflight ready endpoint" "200|401|403" "${ready_code}"

  local notfound_code
  notfound_code="$(http_code GET "${SERVICE_URL}/__nonexistent__" "" "${REPORT_DIR}/preflight_notfound.out")"
  run_test "preflight non-existent endpoint returns 404" "404|401|403" "${notfound_code}"
}

run_selected_scenarios() {
  for scenario in ${SCENARIOS}; do
    case "${scenario}" in
      uc_1a_001_tenant_onboarding)
        scenario_uc_1a_001_tenant_onboarding
        ;;
      uc_1a_002_customer_site_flow)
        scenario_uc_1a_002_customer_site_flow
        ;;
      uc_1a_003_tech_submit_validation)
        scenario_uc_1a_003_tech_submit_validation
        ;;
      *)
        run_skip "scenario ${scenario}" "Unknown scenario"
        ;;
    esac
  done
}

run_preflight_checks
run_selected_scenarios

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

