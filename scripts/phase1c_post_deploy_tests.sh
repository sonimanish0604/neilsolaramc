#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"

SERVICE_URL="${SERVICE_URL:?SERVICE_URL is required}"
REPORT_DIR="${REPORT_DIR:-/workspace/reports}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-}"
SUMMARY_FILE="${SUMMARY_FILE:-${REPORT_DIR}/phase1c_post_deploy_summary.md}"
JUNIT_FILE="${JUNIT_FILE:-${REPORT_DIR}/phase1c_post_deploy_junit.xml}"
EXIT_FILE="${EXIT_FILE:-${REPORT_DIR}/phase1c_post_deploy_exit_code.txt}"

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
  local method="$1"
  local url="$2"
  local payload="$3"
  local out_file="$4"
  http_code "${method}" "${url}" "${payload}" "${out_file}" "false" "${FUNCTIONAL_BEARER_TOKEN}"
}

if [[ -z "${FUNCTIONAL_BEARER_TOKEN}" ]]; then
  run_skip "P1C auth token present" "FUNCTIONAL_BEARER_TOKEN not provided"
  write_reports \
    "Phase 1C Post-Deploy API Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH:-manual}" \
    "${BUILD_ID:-unknown}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  exit 0
fi

ts="$(date +%s)"
customer_name="P1C Cloud Customer ${ts}"
site_name="P1C Cloud Site ${ts}"
tech_uuid="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
scheduled_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

customer_out="${REPORT_DIR}/p1c_customer.json"
customer_code="$(api_call "POST" "${SERVICE_URL}/customers" "{\"name\":\"${customer_name}\",\"address\":\"P1C cloud\",\"status\":\"ACTIVE\"}" "${customer_out}")"
run_test "P1C seed create customer" "200" "${customer_code}"
customer_id="$(json_value id "${customer_out}")"

site_out="${REPORT_DIR}/p1c_site.json"
site_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"${site_name}\",\"address\":\"P1C cloud\",\"capacity_kw\":7.5,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Cloud Supervisor\",\"site_supervisor_phone\":\"+15550110011\",\"site_supervisor_email\":\"cloud.supervisor@example.com\"}"
site_code="$(api_call "POST" "${SERVICE_URL}/sites" "${site_payload}" "${site_out}")"
run_test "P1C seed create site" "200" "${site_code}"
site_id="$(json_value id "${site_out}")"

wo_out="${REPORT_DIR}/p1c_workorder.json"
wo_payload="{\"site_id\":\"${site_id}\",\"assigned_tech_user_id\":\"${tech_uuid}\",\"scheduled_at\":\"${scheduled_at}\"}"
wo_code="$(api_call "POST" "${SERVICE_URL}/workorders" "${wo_payload}" "${wo_out}")"
run_test "P1C seed create workorder" "200" "${wo_code}"
workorder_id="$(json_value id "${wo_out}")"

if [[ -z "${workorder_id}" ]]; then
  run_test "P1C seed workorder id present" "YES" "NO"
  write_reports \
    "Phase 1C Post-Deploy API Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH:-manual}" \
    "${BUILD_ID:-unknown}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  exit 0
fi
run_test "P1C seed workorder id present" "YES" "YES"

# 1
k1="p1c-async-${ts}"
a1_out="${REPORT_DIR}/p1c_api1_1.json"
a2_out="${REPORT_DIR}/p1c_api1_2.json"
a1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report-async" "{\"is_final\":false,\"idempotency_key\":\"${k1}\"}" "${a1_out}")"
a2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report-async" "{\"is_final\":false,\"idempotency_key\":\"${k1}\"}" "${a2_out}")"
run_test "P1C API1 first" "200" "${a1_code}"
run_test "P1C API1 second" "200" "${a2_code}"
j1="$(json_value job_id "${a1_out}")"
j2="$(json_value job_id "${a2_out}")"
run_test "P1C API1 idempotent job" "YES" "$([[ -n "${j1}" && "${j1}" == "${j2}" ]] && echo YES || echo NO)"

# 2
k2="p1c-sync-${ts}"
b1_out="${REPORT_DIR}/p1c_api2_1.json"
b2_out="${REPORT_DIR}/p1c_api2_2.json"
b1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report" "{\"is_final\":false,\"idempotency_key\":\"${k2}\"}" "${b1_out}")"
b2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report" "{\"is_final\":false,\"idempotency_key\":\"${k2}\"}" "${b2_out}")"
run_test "P1C API2 first" "200" "${b1_code}"
run_test "P1C API2 second" "200" "${b2_code}"
run_test "P1C API2 idempotent job" "YES" "$([[ "$(json_value job.job_id "${b1_out}")" == "$(json_value job.job_id "${b2_out}")" ]] && echo YES || echo NO)"

# 3
c1_out="${REPORT_DIR}/p1c_api3_1.json"
c2_out="${REPORT_DIR}/p1c_api3_2.json"
c1_code="$(api_call "POST" "${SERVICE_URL}/workorders/report-jobs/${j1}/run" "" "${c1_out}")"
c2_code="$(api_call "POST" "${SERVICE_URL}/workorders/report-jobs/${j1}/run" "" "${c2_out}")"
run_test "P1C API3 first" "200" "${c1_code}"
run_test "P1C API3 second" "200" "${c2_code}"
run_test "P1C API3 repeat-safe" "YES" "$([[ "$(json_value status "${c1_out}")" == "SUCCEEDED" && "$(json_value status "${c2_out}")" == "SUCCEEDED" ]] && echo YES || echo NO)"

# 4
d1_out="${REPORT_DIR}/p1c_api4_1.json"
d2_out="${REPORT_DIR}/p1c_api4_2.json"
d1_code="$(api_call "POST" "${SERVICE_URL}/workorders/report-jobs/${j1}/retry" "" "${d1_out}")"
d2_code="$(api_call "POST" "${SERVICE_URL}/workorders/report-jobs/${j1}/retry" "" "${d2_out}")"
run_test "P1C API4 first" "200" "${d1_code}"
run_test "P1C API4 second" "200" "${d2_code}"
run_test "P1C API4 repeat-safe" "YES" "$([[ "$(json_value status "${d1_out}")" == "SUCCEEDED" && "$(json_value status "${d2_out}")" == "SUCCEEDED" ]] && echo YES || echo NO)"

# 5
e1_out="${REPORT_DIR}/p1c_api5_1.json"
e2_out="${REPORT_DIR}/p1c_api5_2.json"
e1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/send-approval" "" "${e1_out}")"
e2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/send-approval" "" "${e2_out}")"
run_test "P1C API5 first" "200" "${e1_code}"
run_test "P1C API5 second blocked" "409" "${e2_code}"

# 6
f1_out="${REPORT_DIR}/p1c_api6_1.json"
f2_out="${REPORT_DIR}/p1c_api6_2.json"
f1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/resend-approval" '{"mode":"EXTEND"}' "${f1_out}")"
f2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/resend-approval" '{"mode":"EXTEND"}' "${f2_out}")"
run_test "P1C API6 first" "200" "${f1_code}"
run_test "P1C API6 second" "200" "${f2_code}"
run_test "P1C API6 idempotent event" "YES" "$([[ "$(json_value event_id "${f1_out}")" == "$(json_value event_id "${f2_out}")" ]] && echo YES || echo NO)"

# supersession behavior: NEW_TOKEN should supersede old token
g1_out="${REPORT_DIR}/p1c_api7_new_token.json"
g1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/resend-approval" '{"mode":"NEW_TOKEN"}' "${g1_out}")"
run_test "P1C API7 resend NEW_TOKEN call" "200" "${g1_code}"
old_token="$(last_path_part "$(json_value approval_link "${e1_out}")")"
new_token="$(last_path_part "$(json_value approval_link "${g1_out}")")"
run_test "P1C API7 token rotated" "YES" "$([[ -n "${old_token}" && -n "${new_token}" && "${old_token}" != "${new_token}" ]] && echo YES || echo NO)"

old_view_code="$(curl -sS -o "${REPORT_DIR}/p1c_api7_old_token_view.json" -w "%{http_code}" "${SERVICE_URL}/approve/${old_token}" || true)"
new_view_code="$(curl -sS -o "${REPORT_DIR}/p1c_api7_new_token_view.json" -w "%{http_code}" "${SERVICE_URL}/approve/${new_token}" || true)"
run_test "P1C API7 old token invalid after supersession" "410" "${old_view_code}"
run_test "P1C API7 new token valid" "200" "${new_view_code}"

# retry/backoff behavior with simulated transient report failure
h1_out="${REPORT_DIR}/p1c_api8_async_failfirst.json"
h1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${workorder_id}/generate-report-async" "{\"is_final\":false,\"idempotency_key\":\"p1c-failfirst-${ts}\",\"simulate_failures\":1}" "${h1_out}")"
run_test "P1C API8 enqueue fail-first report job" "200" "${h1_code}"
h_job_id="$(json_value job_id "${h1_out}")"

h2_out="${REPORT_DIR}/p1c_api8_run_failfirst.json"
h2_code="$(api_call "POST" "${SERVICE_URL}/workorders/report-jobs/${h_job_id}/run" "" "${h2_out}")"
run_test "P1C API8 run fail-first job" "200" "${h2_code}"
run_test "P1C API8 status FAILED after transient error" "YES" "$([[ "$(json_value status "${h2_out}")" == "FAILED" ]] && echo YES || echo NO)"
run_test "P1C API8 next_retry_at set" "YES" "$([[ -n "$(json_value next_retry_at "${h2_out}")" ]] && echo YES || echo NO)"

h3_out="${REPORT_DIR}/p1c_api8_retry_after_fail.json"
h3_code="$(api_call "POST" "${SERVICE_URL}/workorders/report-jobs/${h_job_id}/retry" "" "${h3_out}")"
run_test "P1C API8 retry failed job" "200" "${h3_code}"
run_test "P1C API8 status SUCCEEDED after retry" "YES" "$([[ "$(json_value status "${h3_out}")" == "SUCCEEDED" ]] && echo YES || echo NO)"

# correlation id checks on responses
run_test "P1C correlation id in API1 response" "YES" "$([[ -n "$(json_value correlation_id "${a1_out}")" ]] && echo YES || echo NO)"
run_test "P1C correlation id in API5 response" "YES" "$([[ -n "$(json_value correlation_id "${e1_out}")" ]] && echo YES || echo NO)"

write_reports \
  "Phase 1C Post-Deploy API Summary" \
  "${SERVICE_URL}" \
  "${REPORT_BRANCH:-manual}" \
  "${BUILD_ID:-unknown}" \
  "${SUMMARY_FILE}" \
  "${JUNIT_FILE}" \
  "${EXIT_FILE}"

exit 0
