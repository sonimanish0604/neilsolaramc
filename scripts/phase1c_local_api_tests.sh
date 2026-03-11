#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"

ENV_FILE="${ENV_FILE:-.env.local}"
SERVICE_URL="${SERVICE_URL:-http://localhost:8080}"
ADMIN_KEY="${POST_DEPLOY_ADMIN_KEY:-${BOOTSTRAP_ADMIN_KEY:-dev-bootstrap-key}}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-dev-local-token}"

REPORT_DIR="${ROOT_DIR}/reports/phase1c-local"
SUMMARY_FILE="${REPORT_DIR}/summary.md"
JUNIT_FILE="${REPORT_DIR}/junit.xml"
EXIT_FILE="${REPORT_DIR}/exit_code.txt"

export ADMIN_KEY

mkdir -p "${REPORT_DIR}"

json_value() {
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
    else:
        print("")
        raise SystemExit(0)

if cur is None:
    print("")
else:
    print(cur)
PY
}

last_path_part() {
  local input="$1"
  python3 - "$input" <<'PY'
import sys
s = sys.argv[1].strip()
if not s:
    print("")
    raise SystemExit(0)
print(s.rstrip("/").split("/")[-1])
PY
}

api_call() {
  local name="$1"
  local method="$2"
  local url="$3"
  local payload="$4"
  local out_file="$5"
  http_code "${method}" "${url}" "${payload}" "${out_file}" "false" "${FUNCTIONAL_BEARER_TOKEN}"
}

echo "[phase1c] Starting Docker Compose stack"
docker compose --env-file "${ENV_FILE}" up -d --build

echo "[phase1c] Waiting for /health"
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
    "Phase 1C Local API Test Summary" \
    "${SERVICE_URL}" \
    "local" \
    "manual-local" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  cat "${SUMMARY_FILE}"
  exit 1
fi

ts="$(date +%s)"
customer_name="Phase1C Customer ${ts}"
site_name="Phase1C Site ${ts}"
tech_uuid="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
scheduled_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

customer_out="${REPORT_DIR}/seed_customer.json"
customer_payload="{\"name\":\"${customer_name}\",\"address\":\"Phase1C test\",\"status\":\"ACTIVE\"}"
customer_code="$(api_call "seed customer" "POST" "${SERVICE_URL}/customers" "${customer_payload}" "${customer_out}")"
run_test "seed create customer" "200" "${customer_code}"
customer_id="$(json_value id "${customer_out}")"

site_out="${REPORT_DIR}/seed_site.json"
site_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"${site_name}\",\"address\":\"Phase1C test\",\"capacity_kw\":11.2,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Supervisor\",\"site_supervisor_phone\":\"+15550123456\",\"site_supervisor_email\":\"phase1c.supervisor@example.com\"}"
site_code="$(api_call "seed site" "POST" "${SERVICE_URL}/sites" "${site_payload}" "${site_out}")"
run_test "seed create site" "200" "${site_code}"
site_id="$(json_value id "${site_out}")"

wo_out="${REPORT_DIR}/seed_workorder.json"
wo_payload="{\"site_id\":\"${site_id}\",\"assigned_tech_user_id\":\"${tech_uuid}\",\"scheduled_at\":\"${scheduled_at}\"}"
wo_code="$(api_call "seed workorder" "POST" "${SERVICE_URL}/workorders" "${wo_payload}" "${wo_out}")"
run_test "seed create workorder" "200" "${wo_code}"
workorder_id="$(json_value id "${wo_out}")"

if [[ -z "${customer_id}" || -z "${site_id}" || -z "${workorder_id}" ]]; then
  run_test "seed data ids populated" "YES" "NO"
  write_reports \
    "Phase 1C Local API Test Summary" \
    "${SERVICE_URL}" \
    "local" \
    "manual-local" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  cat "${SUMMARY_FILE}"
  exit 1
fi
run_test "seed data ids populated" "YES" "YES"

# 1) generate-report-async idempotency
async_key="phase1c-async-${ts}"
async_payload="{\"is_final\":false,\"idempotency_key\":\"${async_key}\"}"
async_1_out="${REPORT_DIR}/api1_generate_report_async_1.json"
async_2_out="${REPORT_DIR}/api1_generate_report_async_2.json"
async_1_code="$(api_call "api1 async first" "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report-async" "${async_payload}" "${async_1_out}")"
async_2_code="$(api_call "api1 async second" "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report-async" "${async_payload}" "${async_2_out}")"
run_test "API1 generate-report-async first call" "200" "${async_1_code}"
run_test "API1 generate-report-async second call" "200" "${async_2_code}"
async_job_1="$(json_value job_id "${async_1_out}")"
async_job_2="$(json_value job_id "${async_2_out}")"
if [[ "${async_job_1}" == "${async_job_2}" && -n "${async_job_1}" ]]; then
  run_test "API1 idempotency same job_id" "YES" "YES"
else
  run_test "API1 idempotency same job_id" "YES" "NO"
fi

# 2) generate-report sync idempotency
sync_key="phase1c-sync-${ts}"
sync_payload="{\"is_final\":false,\"idempotency_key\":\"${sync_key}\"}"
sync_1_out="${REPORT_DIR}/api2_generate_report_sync_1.json"
sync_2_out="${REPORT_DIR}/api2_generate_report_sync_2.json"
sync_1_code="$(api_call "api2 sync first" "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report" "${sync_payload}" "${sync_1_out}")"
sync_2_code="$(api_call "api2 sync second" "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report" "${sync_payload}" "${sync_2_out}")"
run_test "API2 generate-report first call" "200" "${sync_1_code}"
run_test "API2 generate-report second call" "200" "${sync_2_code}"
sync_job_1="$(json_value job.job_id "${sync_1_out}")"
sync_job_2="$(json_value job.job_id "${sync_2_out}")"
sync_report_1="$(json_value job.generated_report_id "${sync_1_out}")"
sync_report_2="$(json_value job.generated_report_id "${sync_2_out}")"
if [[ "${sync_job_1}" == "${sync_job_2}" && -n "${sync_job_1}" ]]; then
  run_test "API2 idempotency same job_id" "YES" "YES"
else
  run_test "API2 idempotency same job_id" "YES" "NO"
fi
if [[ "${sync_report_1}" == "${sync_report_2}" && -n "${sync_report_1}" ]]; then
  run_test "API2 idempotency same generated_report_id" "YES" "YES"
else
  run_test "API2 idempotency same generated_report_id" "YES" "NO"
fi

# 3) report-jobs/{id}/run idempotency (safe repeated run)
api3_1_out="${REPORT_DIR}/api3_run_job_1.json"
api3_2_out="${REPORT_DIR}/api3_run_job_2.json"
api3_1_code="$(api_call "api3 run first" "POST" "${SERVICE_URL}/workorders/report-jobs/${async_job_1}/run" "" "${api3_1_out}")"
api3_2_code="$(api_call "api3 run second" "POST" "${SERVICE_URL}/workorders/report-jobs/${async_job_1}/run" "" "${api3_2_out}")"
run_test "API3 run report job first call" "200" "${api3_1_code}"
run_test "API3 run report job second call" "200" "${api3_2_code}"
api3_status_1="$(json_value status "${api3_1_out}")"
api3_status_2="$(json_value status "${api3_2_out}")"
if [[ "${api3_status_1}" == "SUCCEEDED" && "${api3_status_2}" == "SUCCEEDED" ]]; then
  run_test "API3 idempotency status remains SUCCEEDED" "YES" "YES"
else
  run_test "API3 idempotency status remains SUCCEEDED" "YES" "NO"
fi

# 4) report-jobs/{id}/retry idempotency on already-successful job
api4_1_out="${REPORT_DIR}/api4_retry_job_1.json"
api4_2_out="${REPORT_DIR}/api4_retry_job_2.json"
api4_1_code="$(api_call "api4 retry first" "POST" "${SERVICE_URL}/workorders/report-jobs/${async_job_1}/retry" "" "${api4_1_out}")"
api4_2_code="$(api_call "api4 retry second" "POST" "${SERVICE_URL}/workorders/report-jobs/${async_job_1}/retry" "" "${api4_2_out}")"
run_test "API4 retry report job first call" "200" "${api4_1_code}"
run_test "API4 retry report job second call" "200" "${api4_2_code}"
api4_status_1="$(json_value status "${api4_1_out}")"
api4_status_2="$(json_value status "${api4_2_out}")"
if [[ "${api4_status_1}" == "SUCCEEDED" && "${api4_status_2}" == "SUCCEEDED" ]]; then
  run_test "API4 idempotency status remains SUCCEEDED" "YES" "YES"
else
  run_test "API4 idempotency status remains SUCCEEDED" "YES" "NO"
fi

# 5) send-approval idempotency (first accepted, second blocked)
api5_1_out="${REPORT_DIR}/api5_send_approval_1.json"
api5_2_out="${REPORT_DIR}/api5_send_approval_2.json"
api5_1_code="$(api_call "api5 send first" "POST" "${SERVICE_URL}/workorders/${workorder_id}/send-approval" "" "${api5_1_out}")"
api5_2_code="$(api_call "api5 send second" "POST" "${SERVICE_URL}/workorders/${workorder_id}/send-approval" "" "${api5_2_out}")"
run_test "API5 send-approval first call" "200" "${api5_1_code}"
run_test "API5 send-approval second call blocked" "409" "${api5_2_code}"
api5_event_id="$(json_value event_id "${api5_1_out}")"

# 6) resend-approval EXTEND idempotency (same active event id)
api6_payload='{"mode":"EXTEND"}'
api6_1_out="${REPORT_DIR}/api6_resend_approval_1.json"
api6_2_out="${REPORT_DIR}/api6_resend_approval_2.json"
api6_1_code="$(api_call "api6 resend first" "POST" "${SERVICE_URL}/workorders/${workorder_id}/resend-approval" "${api6_payload}" "${api6_1_out}")"
api6_2_code="$(api_call "api6 resend second" "POST" "${SERVICE_URL}/workorders/${workorder_id}/resend-approval" "${api6_payload}" "${api6_2_out}")"
run_test "API6 resend-approval first call" "200" "${api6_1_code}"
run_test "API6 resend-approval second call" "200" "${api6_2_code}"
api6_event_1="$(json_value event_id "${api6_1_out}")"
api6_event_2="$(json_value event_id "${api6_2_out}")"
if [[ "${api6_event_1}" == "${api6_event_2}" && -n "${api6_event_1}" ]]; then
  run_test "API6 idempotency same event_id" "YES" "YES"
else
  run_test "API6 idempotency same event_id" "YES" "NO"
fi
if [[ -n "${api5_event_id}" && "${api6_event_1}" == "${api5_event_id}" ]]; then
  run_test "API6 extends existing approval event" "YES" "YES"
else
  run_test "API6 extends existing approval event" "YES" "NO"
fi

# 7) token supersession: NEW_TOKEN rotates and invalidates old token
api7_out="${REPORT_DIR}/api7_resend_new_token.json"
api7_code="$(api_call "api7 resend new token" "POST" "${SERVICE_URL}/workorders/${workorder_id}/resend-approval" '{"mode":"NEW_TOKEN"}' "${api7_out}")"
run_test "API7 resend-approval NEW_TOKEN call" "200" "${api7_code}"
old_token="$(last_path_part "$(json_value approval_link "${api5_1_out}")")"
new_token="$(last_path_part "$(json_value approval_link "${api7_out}")")"
if [[ -n "${old_token}" && -n "${new_token}" && "${old_token}" != "${new_token}" ]]; then
  run_test "API7 token rotated" "YES" "YES"
else
  run_test "API7 token rotated" "YES" "NO"
fi
old_view_code="$(curl -sS -o "${REPORT_DIR}/api7_old_token_view.json" -w "%{http_code}" "${SERVICE_URL}/approve/${old_token}" || true)"
new_view_code="$(curl -sS -o "${REPORT_DIR}/api7_new_token_view.json" -w "%{http_code}" "${SERVICE_URL}/approve/${new_token}" || true)"
run_test "API7 old token invalid after supersession" "410" "${old_view_code}"
run_test "API7 new token valid" "200" "${new_view_code}"

# 8) report retry/backoff: simulated transient failure then retry success
api8_key="phase1c-failfirst-${ts}"
api8_async_payload="{\"is_final\":false,\"idempotency_key\":\"${api8_key}\",\"simulate_failures\":1}"
api8_1_out="${REPORT_DIR}/api8_generate_report_async_failfirst.json"
api8_1_code="$(api_call "api8 async failfirst" "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report-async" "${api8_async_payload}" "${api8_1_out}")"
run_test "API8 enqueue fail-first report job" "200" "${api8_1_code}"
api8_job_id="$(json_value job_id "${api8_1_out}")"
api8_2_out="${REPORT_DIR}/api8_run_failfirst_job.json"
api8_2_code="$(api_call "api8 run failfirst" "POST" "${SERVICE_URL}/workorders/report-jobs/${api8_job_id}/run" "" "${api8_2_out}")"
run_test "API8 run fail-first job" "200" "${api8_2_code}"
if [[ "$(json_value status "${api8_2_out}")" == "FAILED" ]]; then
  run_test "API8 status FAILED after transient error" "YES" "YES"
else
  run_test "API8 status FAILED after transient error" "YES" "NO"
fi
if [[ -n "$(json_value next_retry_at "${api8_2_out}")" ]]; then
  run_test "API8 next_retry_at set" "YES" "YES"
else
  run_test "API8 next_retry_at set" "YES" "NO"
fi
api8_3_out="${REPORT_DIR}/api8_retry_failfirst_job.json"
api8_3_code="$(api_call "api8 retry failfirst" "POST" "${SERVICE_URL}/workorders/report-jobs/${api8_job_id}/retry" "" "${api8_3_out}")"
run_test "API8 retry failed job" "200" "${api8_3_code}"
if [[ "$(json_value status "${api8_3_out}")" == "SUCCEEDED" ]]; then
  run_test "API8 status SUCCEEDED after retry" "YES" "YES"
else
  run_test "API8 status SUCCEEDED after retry" "YES" "NO"
fi

if [[ -n "$(json_value correlation_id "${async_1_out}")" ]]; then
  run_test "API1 response has correlation_id" "YES" "YES"
else
  run_test "API1 response has correlation_id" "YES" "NO"
fi
if [[ -n "$(json_value correlation_id "${api5_1_out}")" ]]; then
  run_test "API5 response has correlation_id" "YES" "YES"
else
  run_test "API5 response has correlation_id" "YES" "NO"
fi

write_reports \
  "Phase 1C Local API Test Summary" \
  "${SERVICE_URL}" \
  "local" \
  "manual-local" \
  "${SUMMARY_FILE}" \
  "${JUNIT_FILE}" \
  "${EXIT_FILE}"

cat "${SUMMARY_FILE}"
if [[ "$(cat "${EXIT_FILE}")" != "0" ]]; then
  exit 1
fi

echo "[phase1c] PASSED"
echo "[phase1c] Reports:"
echo "- ${SUMMARY_FILE}"
echo "- ${JUNIT_FILE}"
echo "- ${EXIT_FILE}"
