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

if [[ "${code}" != "200" ]]; then
  echo "[phase1a] health check failed with HTTP ${code}"
  cat /tmp/phase1a_health.out || true
  exit 1
fi

echo "[phase1a] Bootstrapping local auth-disabled user context"
bootstrap_ts="$(date +%s)"
bootstrap_tenant_payload="{\"name\":\"phase1a-local-bootstrap-${bootstrap_ts}\",\"plan_code\":\"TRIAL\",\"status\":\"ACTIVE\"}"
bootstrap_tenant_code="$(curl -s -o /tmp/phase1a_bootstrap_tenant.out -w "%{http_code}" -X POST "${API_URL}/admin/tenants" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d "${bootstrap_tenant_payload}")"
if [[ "${bootstrap_tenant_code}" != "200" ]]; then
  echo "[phase1a] bootstrap tenant create failed with HTTP ${bootstrap_tenant_code}"
  cat /tmp/phase1a_bootstrap_tenant.out || true
  exit 1
fi
bootstrap_tenant_id="$(python3 -c 'import json;print(json.load(open("/tmp/phase1a_bootstrap_tenant.out"))["id"])')"

local_user_payload="{\"tenant_id\":\"${bootstrap_tenant_id}\",\"firebase_uid\":\"local-dev-user\",\"name\":\"Local Dev Owner\",\"email\":\"local-dev-owner@example.com\",\"status\":\"ACTIVE\"}"
local_user_code="$(curl -s -o /tmp/phase1a_bootstrap_user.out -w "%{http_code}" -X POST "${API_URL}/admin/users" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d "${local_user_payload}")"
local_user_id=""
if [[ "${local_user_code}" == "200" ]]; then
  local_user_id="$(python3 -c 'import json;print(json.load(open("/tmp/phase1a_bootstrap_user.out"))["id"])')"
elif [[ "${local_user_code}" == "409" ]]; then
  echo "[phase1a] local-dev-user already exists; reusing existing identity"
else
  echo "[phase1a] bootstrap local-dev-user create failed with HTTP ${local_user_code}"
  cat /tmp/phase1a_bootstrap_user.out || true
  exit 1
fi

if [[ -n "${local_user_id}" ]]; then
  local_role_code="$(curl -s -o /tmp/phase1a_bootstrap_role.out -w "%{http_code}" -X POST "${API_URL}/admin/users/${local_user_id}/roles" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Key: ${ADMIN_KEY}" \
    -d '{"role":"OWNER"}')"
  if [[ "${local_role_code}" != "200" && "${local_role_code}" != "409" ]]; then
    echo "[phase1a] bootstrap OWNER role assign failed with HTTP ${local_role_code}"
    cat /tmp/phase1a_bootstrap_role.out || true
    exit 1
  fi
fi

export SERVICE_URL="${API_URL}"
export REPORT_DIR
export REPORT_BRANCH="local"
export BUILD_ID="manual-local"
export POST_DEPLOY_ADMIN_KEY="${ADMIN_KEY}"
export FUNCTIONAL_BEARER_TOKEN="dev-local-token"
export FUNCTIONAL_APPROVAL_TOKEN="${FUNCTIONAL_APPROVAL_TOKEN:-}"
export SUMMARY_FILE
export JUNIT_FILE
export EXIT_FILE
export SUITE_TITLE="Phase 1A Local Functional Test Summary"
export SCENARIOS="uc_1a_001_tenant_onboarding uc_1a_002_customer_site_flow uc_1a_003_tech_submit_validation"

if [[ "${RUN_PHASE1B_APPROVAL_SCENARIO:-false}" == "true" ]]; then
  export SCENARIOS="${SCENARIOS} uc_1b_001_approval_token_flow"
fi

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
