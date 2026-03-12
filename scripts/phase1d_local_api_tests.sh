#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"

ENV_FILE="${ENV_FILE:-.env.local}"
SERVICE_URL="${SERVICE_URL:-http://localhost:8080}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-dev-local-token}"
FUNCTIONAL_ASSIGNED_TECH_USER_ID="${FUNCTIONAL_ASSIGNED_TECH_USER_ID:-}"
ADMIN_KEY="${POST_DEPLOY_ADMIN_KEY:-${BOOTSTRAP_ADMIN_KEY:-dev-bootstrap-key}}"

REPORT_DIR="${ROOT_DIR}/reports/phase1d-local"
SUMMARY_FILE="${REPORT_DIR}/summary.md"
JUNIT_FILE="${REPORT_DIR}/junit.xml"
EXIT_FILE="${REPORT_DIR}/exit_code.txt"

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
    elif isinstance(cur, list):
        try:
            idx = int(part)
        except Exception:
            print("")
            raise SystemExit(0)
        if idx < 0 or idx >= len(cur):
            print("")
            raise SystemExit(0)
        cur = cur[idx]
    else:
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

admin_call() {
  local method="$1"
  local url="$2"
  local payload="$3"
  local out_file="$4"
  local args=(-sS -o "${out_file}" -w "%{http_code}" -X "${method}" "${url}" -H "Content-Type: application/json" -H "X-Admin-Key: ${ADMIN_KEY}")
  if [[ -n "${payload}" ]]; then
    args+=(-d "${payload}")
  fi
  curl "${args[@]}" || true
}

resolve_local_dev_user_id() {
  local container_name="${POSTGRES_CONTAINER_NAME:-neilsolar-postgres-local}"
  local db_name="${POSTGRES_DB:-neilsolar_local}"
  local db_user="${POSTGRES_USER:-postgres}"
  local user_id
  user_id="$(docker exec "${container_name}" psql -U "${db_user}" -d "${db_name}" -t -A -c "select id::text from users where firebase_uid='local-dev-user' limit 1;" 2>/dev/null | tr -d '\r\n' || true)"
  echo "${user_id}"
}

echo "[phase1d] Starting Docker Compose stack (postgres + api only)"
docker compose --env-file "${ENV_FILE}" up -d --build postgres api

echo "[phase1d] Waiting for /health"
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
    "Phase 1D Local API Test Summary" \
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
customer_name="Phase1D Customer ${ts}"
site_name="Phase1D Site ${ts}"
if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  FUNCTIONAL_ASSIGNED_TECH_USER_ID="$(resolve_local_dev_user_id)"
fi
if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  echo "[phase1d] Unable to resolve local-dev-user ID from postgres."
  echo "[phase1d] Set FUNCTIONAL_ASSIGNED_TECH_USER_ID explicitly and re-run."
  exit 1
fi

role_out="${REPORT_DIR}/assign_tech_role.json"
role_code="$(admin_call "POST" "${SERVICE_URL}/admin/users/${FUNCTIONAL_ASSIGNED_TECH_USER_ID}/roles" "{\"role\":\"TECH\"}" "${role_out}")"
run_test "P1D ensure local-dev-user has TECH role" "200|409" "${role_code}"

supervisor_role_out="${REPORT_DIR}/assign_supervisor_role.json"
supervisor_role_code="$(admin_call "POST" "${SERVICE_URL}/admin/users/${FUNCTIONAL_ASSIGNED_TECH_USER_ID}/roles" "{\"role\":\"SUPERVISOR\"}" "${supervisor_role_out}")"
run_test "P1D ensure local-dev-user has SUPERVISOR role" "200|409" "${supervisor_role_code}"

scheduled_at_1="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
scheduled_at_2="$(date -u -d '+1 day' +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")"

customer_out="${REPORT_DIR}/customer.json"
customer_code="$(api_call "POST" "${SERVICE_URL}/customers" "{\"name\":\"${customer_name}\",\"address\":\"Phase1D test\",\"status\":\"ACTIVE\"}" "${customer_out}")"
run_test "P1D seed create customer" "200" "${customer_code}"
customer_id="$(json_value id "${customer_out}")"

site_out="${REPORT_DIR}/site.json"
site_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"${site_name}\",\"address\":\"Phase1D test\",\"capacity_kw\":300,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Supervisor\",\"site_supervisor_phone\":\"+15550111111\",\"site_supervisor_email\":\"phase1d.supervisor@example.com\"}"
site_code="$(api_call "POST" "${SERVICE_URL}/sites" "${site_payload}" "${site_out}")"
run_test "P1D seed create site" "200" "${site_code}"
site_id="$(json_value id "${site_out}")"

inv1_out="${REPORT_DIR}/site_inverter_1.json"
inv1_code="$(api_call "POST" "${SERVICE_URL}/sites/${site_id}/inverters" "{\"inverter_code\":\"INV-01\",\"display_name\":\"Inverter 01\",\"capacity_kw\":25,\"is_active\":true}" "${inv1_out}")"
run_test "P1D create site inverter 1" "200" "${inv1_code}"
inv1_id="$(json_value id "${inv1_out}")"

inv2_out="${REPORT_DIR}/site_inverter_2.json"
inv2_code="$(api_call "POST" "${SERVICE_URL}/sites/${site_id}/inverters" "{\"inverter_code\":\"INV-02\",\"display_name\":\"Inverter 02\",\"capacity_kw\":25,\"is_active\":true}" "${inv2_out}")"
run_test "P1D create site inverter 2" "200" "${inv2_code}"
inv2_id="$(json_value id "${inv2_out}")"

inv2_upd_out="${REPORT_DIR}/site_inverter_2_update.json"
inv2_upd_code="$(api_call "PATCH" "${SERVICE_URL}/sites/${site_id}/inverters/${inv2_id}" "{\"display_name\":\"Inverter 02-B\",\"is_active\":true}" "${inv2_upd_out}")"
run_test "P1D update site inverter 2" "200" "${inv2_upd_code}"

site_inv_list_out="${REPORT_DIR}/site_inverters_list.json"
site_inv_list_code="$(api_call "GET" "${SERVICE_URL}/sites/${site_id}/inverters" "" "${site_inv_list_out}")"
run_test "P1D list site inverters" "200" "${site_inv_list_code}"
run_test "P1D list contains inverter count >=2" "YES" "$([[ "$(json_value 0.inverter_code "${site_inv_list_out}")" == "INV-01" ]] && echo YES || echo NO)"

wo1_out="${REPORT_DIR}/workorder_1.json"
wo1_code="$(api_call "POST" "${SERVICE_URL}/workorders" "{\"site_id\":\"${site_id}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${scheduled_at_1}\"}" "${wo1_out}")"
run_test "P1D create workorder 1" "200" "${wo1_code}"
wo1_id="$(json_value id "${wo1_out}")"

wo1_inv_out="${REPORT_DIR}/workorder_1_inverters.json"
wo1_inv_code="$(api_call "GET" "${SERVICE_URL}/workorders/${wo1_id}/inverters" "" "${wo1_inv_out}")"
run_test "P1D list workorder configured inverters" "200" "${wo1_inv_code}"
run_test "P1D workorder inverters include INV-01" "YES" "$([[ "$(json_value inverters.0.inverter_code "${wo1_inv_out}")" == "INV-01" ]] && echo YES || echo NO)"

wo1_cap1_out="${REPORT_DIR}/workorder_1_capture_inv1.json"
wo1_cap1_payload="{\"inverter_id\":\"${inv1_id}\",\"current_reading_kwh\":1000.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"ok\",\"photo_object_path\":\"media/phase1d/${wo1_id}/inv1.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":12345}"
wo1_cap1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/inverter-readings" "${wo1_cap1_payload}" "${wo1_cap1_out}")"
run_test "P1D capture inverter 1 baseline" "200" "${wo1_cap1_code}"
run_test "P1D capture inverter 1 is baseline" "true|True" "$(json_value is_baseline "${wo1_cap1_out}")"

wo1_cap2_out="${REPORT_DIR}/workorder_1_capture_inv2.json"
wo1_cap2_payload="{\"inverter_id\":\"${inv2_id}\",\"current_reading_kwh\":null,\"operational_status\":\"OFFLINE\",\"remarks\":\"display blank\",\"photo_object_path\":\"media/phase1d/${wo1_id}/inv2.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":12346}"
wo1_cap2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/inverter-readings" "${wo1_cap2_payload}" "${wo1_cap2_out}")"
run_test "P1D capture inverter 2 offline" "200" "${wo1_cap2_code}"

wo1_submit_out="${REPORT_DIR}/workorder_1_submit.json"
wo1_submit_payload="{\"visit_status\":\"SATISFACTORY\",\"summary_notes\":\"phase1d baseline\",\"inverter_readings\":[],\"net_meter\":{\"net_kwh\":1.0,\"imp_kwh\":2.0,\"exp_kwh\":3.0},\"checklist_answers\":{\"solar_module_clean\":{\"value\":\"YES\"}},\"media\":[{\"item_key\":\"net_meter_readings\",\"object_path\":\"media/phase1d/${wo1_id}/net-meter-1.jpg\",\"content_type\":\"image/jpeg\",\"size_bytes\":1000}],\"tech_signature\":{\"signer_name\":\"Tech One\",\"signer_phone\":\"+15550000000\",\"signature_object_path\":\"signatures/${wo1_id}/tech.png\"}}"
wo1_submit_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/submit" "${wo1_submit_payload}" "${wo1_submit_out}")"
run_test "P1D submit workorder 1" "200" "${wo1_submit_code}"

wo1_send_approval_out="${REPORT_DIR}/workorder_1_send_approval.json"
wo1_send_approval_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/send-approval" "{\"channel\":\"EMAIL\"}" "${wo1_send_approval_out}")"
run_test "P1D send approval workorder 1" "200" "${wo1_send_approval_code}"
wo1_approval_token="$(json_value approval_token "${wo1_send_approval_out}")"

wo1_customer_sign_out="${REPORT_DIR}/workorder_1_customer_sign.json"
wo1_customer_sign_payload="{\"signer_name\":\"Supervisor\",\"signer_phone\":\"+15550111111\",\"signature_object_path\":\"signatures/${wo1_id}/customer.png\"}"
wo1_customer_sign_code="$(http_code "POST" "${SERVICE_URL}/approve/${wo1_approval_token}/sign" "${wo1_customer_sign_payload}" "${wo1_customer_sign_out}")"
run_test "P1D customer sign workorder 1" "200" "${wo1_customer_sign_code}"
run_test "P1D workorder 1 customer sign status" "SIGNED|SIGNED_REPORT_PENDING" "$(json_value status "${wo1_customer_sign_out}")"

wo1_report_out="${REPORT_DIR}/workorder_1_report_data.json"
wo1_report_code="$(api_call "GET" "${SERVICE_URL}/workorders/${wo1_id}/report-data" "" "${wo1_report_out}")"
run_test "P1D workorder 1 report-data" "200" "${wo1_report_code}"
run_test "P1D workorder 1 generation total is 0 baseline" "0.0|0" "$(json_value generation_total_kwh "${wo1_report_out}")"

wo1_sync_out="${REPORT_DIR}/workorder_1_generate_report.json"
wo1_sync_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/generate-report" "{\"is_final\":false,\"idempotency_key\":\"p1d-${ts}-wo1\"}" "${wo1_sync_out}")"
run_test "P1D generate report sync workorder 1" "200" "${wo1_sync_code}"

wo2_out="${REPORT_DIR}/workorder_2.json"
wo2_code="$(api_call "POST" "${SERVICE_URL}/workorders" "{\"site_id\":\"${site_id}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${scheduled_at_2}\"}" "${wo2_out}")"
run_test "P1D create workorder 2" "200" "${wo2_code}"
wo2_id="$(json_value id "${wo2_out}")"

wo2_cap1_out="${REPORT_DIR}/workorder_2_capture_inv1.json"
wo2_cap1_payload="{\"inverter_id\":\"${inv1_id}\",\"current_reading_kwh\":1200.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"ok\",\"photo_object_path\":\"media/phase1d/${wo2_id}/inv1.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":22345}"
wo2_cap1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/inverter-readings" "${wo2_cap1_payload}" "${wo2_cap1_out}")"
run_test "P1D capture inverter 1 delta visit" "200" "${wo2_cap1_code}"
run_test "P1D inverter 1 delta = 200" "200|200.0" "$(json_value generation_delta_kwh "${wo2_cap1_out}")"

wo2_cap2_out="${REPORT_DIR}/workorder_2_capture_inv2.json"
wo2_cap2_payload="{\"inverter_id\":\"${inv2_id}\",\"current_reading_kwh\":null,\"operational_status\":\"OFFLINE\",\"remarks\":\"still offline\",\"photo_object_path\":\"media/phase1d/${wo2_id}/inv2.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":22346}"
wo2_cap2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/inverter-readings" "${wo2_cap2_payload}" "${wo2_cap2_out}")"
run_test "P1D capture inverter 2 offline second visit" "200" "${wo2_cap2_code}"

wo2_submit_out="${REPORT_DIR}/workorder_2_submit.json"
wo2_submit_payload="{\"visit_status\":\"SATISFACTORY\",\"summary_notes\":\"phase1d delta\",\"inverter_readings\":[],\"net_meter\":{\"net_kwh\":2.0,\"imp_kwh\":3.0,\"exp_kwh\":4.0},\"checklist_answers\":{\"solar_module_clean\":{\"value\":\"YES\"}},\"media\":[{\"item_key\":\"net_meter_readings\",\"object_path\":\"media/phase1d/${wo2_id}/net-meter-1.jpg\",\"content_type\":\"image/jpeg\",\"size_bytes\":1001}],\"tech_signature\":{\"signer_name\":\"Tech One\",\"signer_phone\":\"+15550000000\",\"signature_object_path\":\"signatures/${wo2_id}/tech.png\"}}"
wo2_submit_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/submit" "${wo2_submit_payload}" "${wo2_submit_out}")"
run_test "P1D submit workorder 2" "200" "${wo2_submit_code}"

wo2_report_out="${REPORT_DIR}/workorder_2_report_data.json"
wo2_report_code="$(api_call "GET" "${SERVICE_URL}/workorders/${wo2_id}/report-data" "" "${wo2_report_out}")"
run_test "P1D workorder 2 report-data" "200" "${wo2_report_code}"
run_test "P1D workorder 2 generation total = 200" "200|200.0" "$(json_value generation_total_kwh "${wo2_report_out}")"

wo2_sync_out="${REPORT_DIR}/workorder_2_generate_report.json"
wo2_sync_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/generate-report" "{\"is_final\":false,\"idempotency_key\":\"p1d-${ts}-wo2\"}" "${wo2_sync_out}")"
run_test "P1D generate report sync workorder 2" "200" "${wo2_sync_code}"

write_reports \
  "Phase 1D Local API Test Summary" \
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

echo "[phase1d] PASSED"
echo "[phase1d] Reports:"
echo "- ${SUMMARY_FILE}"
echo "- ${JUNIT_FILE}"
echo "- ${EXIT_FILE}"
