#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SERVICE_URL="${SERVICE_URL:?SERVICE_URL is required}"
REPORT_DIR="${REPORT_DIR:-/workspace/reports}"
REPORT_BRANCH="${REPORT_BRANCH:-manual}"
ADMIN_KEY="${POST_DEPLOY_ADMIN_KEY:-dev-bootstrap-key}"
RUN_STATEFUL_TESTS="${RUN_STATEFUL_POST_DEPLOY_TESTS:-false}"

mkdir -p "${REPORT_DIR}"

export SERVICE_URL
export REPORT_DIR
export REPORT_BRANCH
export BUILD_ID="${BUILD_ID:-unknown}"
export POST_DEPLOY_ADMIN_KEY="${ADMIN_KEY}"
export FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-}"
export SUMMARY_FILE="${REPORT_DIR}/post_deploy_summary.md"
export JUNIT_FILE="${REPORT_DIR}/post_deploy_junit.xml"
export EXIT_FILE="${REPORT_DIR}/post_deploy_exit_code.txt"
export SUITE_TITLE="Post-Deploy API Functional Test Summary"

if [[ "${RUN_STATEFUL_TESTS}" == "true" ]]; then
  export SCENARIOS="uc_1a_001_tenant_onboarding uc_1a_002_customer_site_flow uc_1a_003_tech_submit_validation"
else
  export SCENARIOS=""
fi

bash "${ROOT_DIR}/scripts/functional/run_functional_suite.sh" || true

# Preserve existing behavior: this script writes exit code to a file and exits 0.
if [[ ! -f "${EXIT_FILE}" ]]; then
  echo "1" > "${EXIT_FILE}"
fi

if [[ "$(cat "${EXIT_FILE}")" != "0" ]]; then
  echo "Post-deploy API tests reported failures."
else
  echo "Post-deploy API tests passed."
fi

exit 0

