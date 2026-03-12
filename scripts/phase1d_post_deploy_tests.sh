#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"

SERVICE_URL="${SERVICE_URL:?SERVICE_URL is required}"
REPORT_DIR="${REPORT_DIR:-/workspace/reports}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-}"
FUNCTIONAL_ASSIGNED_TECH_USER_ID="${FUNCTIONAL_ASSIGNED_TECH_USER_ID:-}"
SUMMARY_FILE="${SUMMARY_FILE:-${REPORT_DIR}/phase1d_post_deploy_summary.md}"
JUNIT_FILE="${JUNIT_FILE:-${REPORT_DIR}/phase1d_post_deploy_junit.xml}"
EXIT_FILE="${EXIT_FILE:-${REPORT_DIR}/phase1d_post_deploy_exit_code.txt}"

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

if [[ -z "${FUNCTIONAL_BEARER_TOKEN}" ]]; then
  run_skip "P1D auth token present" "FUNCTIONAL_BEARER_TOKEN not provided"
  write_reports \
    "Phase 1D Post-Deploy API Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH:-manual}" \
    "${BUILD_ID:-unknown}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  exit 0
fi

ts="$(date +%s)"
customer_name="P1D Cloud Customer ${ts}"
site_name="P1D Cloud Site ${ts}"
if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  run_skip "P1D assigned tech user id provided" "FUNCTIONAL_ASSIGNED_TECH_USER_ID not set"
  write_reports \
    "Phase 1D Post-Deploy API Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH:-manual}" \
    "${BUILD_ID:-unknown}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  exit 0
fi
scheduled_at_1="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
scheduled_at_2="$(date -u -d '+1 day' +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")"

customer_out="${REPORT_DIR}/p1d_customer.json"
customer_code="$(api_call "POST" "${SERVICE_URL}/customers" "{\"name\":\"${customer_name}\",\"address\":\"P1D cloud\",\"status\":\"ACTIVE\"}" "${customer_out}")"
run_test "P1D seed create customer" "200" "${customer_code}"
customer_id="$(json_value id "${customer_out}")"

site_out="${REPORT_DIR}/p1d_site.json"
site_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"${site_name}\",\"address\":\"P1D cloud\",\"capacity_kw\":300,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Cloud Supervisor\",\"site_supervisor_phone\":\"+15550110011\",\"site_supervisor_email\":\"p1d.supervisor@example.com\"}"
site_code="$(api_call "POST" "${SERVICE_URL}/sites" "${site_payload}" "${site_out}")"
run_test "P1D seed create site" "200" "${site_code}"
site_id="$(json_value id "${site_out}")"

inv1_out="${REPORT_DIR}/p1d_inv1.json"
inv1_code="$(api_call "POST" "${SERVICE_URL}/sites/${site_id}/inverters" "{\"inverter_code\":\"INV-01\",\"display_name\":\"Inverter 01\",\"capacity_kw\":25,\"is_active\":true}" "${inv1_out}")"
run_test "P1D create inverter 1" "200" "${inv1_code}"
inv1_id="$(json_value id "${inv1_out}")"

inv2_out="${REPORT_DIR}/p1d_inv2.json"
inv2_code="$(api_call "POST" "${SERVICE_URL}/sites/${site_id}/inverters" "{\"inverter_code\":\"INV-02\",\"display_name\":\"Inverter 02\",\"capacity_kw\":25,\"is_active\":true}" "${inv2_out}")"
run_test "P1D create inverter 2" "200" "${inv2_code}"
inv2_id="$(json_value id "${inv2_out}")"

inv2_upd_out="${REPORT_DIR}/p1d_inv2_patch.json"
inv2_upd_code="$(api_call "PATCH" "${SERVICE_URL}/sites/${site_id}/inverters/${inv2_id}" "{\"display_name\":\"Inverter 02-B\",\"is_active\":true}" "${inv2_upd_out}")"
run_test "P1D update inverter 2" "200" "${inv2_upd_code}"

wo1_out="${REPORT_DIR}/p1d_wo1.json"
wo1_code="$(api_call "POST" "${SERVICE_URL}/workorders" "{\"site_id\":\"${site_id}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${scheduled_at_1}\"}" "${wo1_out}")"
run_test "P1D create workorder 1" "200" "${wo1_code}"
wo1_id="$(json_value id "${wo1_out}")"

wo1_inv_out="${REPORT_DIR}/p1d_wo1_inverters.json"
wo1_inv_code="$(api_call "GET" "${SERVICE_URL}/workorders/${wo1_id}/inverters" "" "${wo1_inv_out}")"
run_test "P1D list configured inverters for workorder" "200" "${wo1_inv_code}"

wo1_cap1_out="${REPORT_DIR}/p1d_wo1_cap1.json"
wo1_cap1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/inverter-readings" "{\"inverter_id\":\"${inv1_id}\",\"current_reading_kwh\":1000.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"ok\",\"photo_object_path\":\"media/p1d/${wo1_id}/inv1.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1111}" "${wo1_cap1_out}")"
run_test "P1D capture baseline inverter 1" "200" "${wo1_cap1_code}"
run_test "P1D baseline flag set" "true|True" "$(json_value is_baseline "${wo1_cap1_out}")"

wo1_cap2_out="${REPORT_DIR}/p1d_wo1_cap2.json"
wo1_cap2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/inverter-readings" "{\"inverter_id\":\"${inv2_id}\",\"current_reading_kwh\":null,\"operational_status\":\"OFFLINE\",\"remarks\":\"offline\",\"photo_object_path\":\"media/p1d/${wo1_id}/inv2.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1112}" "${wo1_cap2_out}")"
run_test "P1D capture inverter 2 offline" "200" "${wo1_cap2_code}"

wo1_submit_out="${REPORT_DIR}/p1d_wo1_submit.json"
wo1_submit_payload="{\"visit_status\":\"SATISFACTORY\",\"summary_notes\":\"p1d baseline\",\"inverter_readings\":[],\"net_meter\":{\"net_kwh\":1.0,\"imp_kwh\":2.0,\"exp_kwh\":3.0},\"checklist_answers\":{\"solar_module_clean\":{\"value\":\"YES\"}},\"media\":[{\"item_key\":\"net_meter_readings\",\"object_path\":\"media/p1d/${wo1_id}/net-meter.jpg\",\"content_type\":\"image/jpeg\",\"size_bytes\":1000}],\"tech_signature\":{\"signer_name\":\"Tech One\",\"signer_phone\":\"+15550000000\",\"signature_object_path\":\"signatures/${wo1_id}/tech.png\"}}"
wo1_submit_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo1_id}/submit" "${wo1_submit_payload}" "${wo1_submit_out}")"
run_test "P1D submit workorder 1" "200" "${wo1_submit_code}"

wo1_report_out="${REPORT_DIR}/p1d_wo1_report_data.json"
wo1_report_code="$(api_call "GET" "${SERVICE_URL}/workorders/${wo1_id}/report-data" "" "${wo1_report_out}")"
run_test "P1D report-data workorder 1" "200" "${wo1_report_code}"
run_test "P1D generation total baseline visit" "0.0|0" "$(json_value generation_total_kwh "${wo1_report_out}")"

wo2_out="${REPORT_DIR}/p1d_wo2.json"
wo2_code="$(api_call "POST" "${SERVICE_URL}/workorders" "{\"site_id\":\"${site_id}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${scheduled_at_2}\"}" "${wo2_out}")"
run_test "P1D create workorder 2" "200" "${wo2_code}"
wo2_id="$(json_value id "${wo2_out}")"

wo2_cap1_out="${REPORT_DIR}/p1d_wo2_cap1.json"
wo2_cap1_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/inverter-readings" "{\"inverter_id\":\"${inv1_id}\",\"current_reading_kwh\":1200.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"ok\",\"photo_object_path\":\"media/p1d/${wo2_id}/inv1.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":2111}" "${wo2_cap1_out}")"
run_test "P1D capture delta inverter 1" "200" "${wo2_cap1_code}"
run_test "P1D delta equals 200" "200|200.0" "$(json_value generation_delta_kwh "${wo2_cap1_out}")"

wo2_cap2_out="${REPORT_DIR}/p1d_wo2_cap2.json"
wo2_cap2_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/inverter-readings" "{\"inverter_id\":\"${inv2_id}\",\"current_reading_kwh\":null,\"operational_status\":\"OFFLINE\",\"remarks\":\"offline\",\"photo_object_path\":\"media/p1d/${wo2_id}/inv2.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":2112}" "${wo2_cap2_out}")"
run_test "P1D capture inverter 2 offline second visit" "200" "${wo2_cap2_code}"

wo2_submit_out="${REPORT_DIR}/p1d_wo2_submit.json"
wo2_submit_payload="{\"visit_status\":\"SATISFACTORY\",\"summary_notes\":\"p1d delta\",\"inverter_readings\":[],\"net_meter\":{\"net_kwh\":2.0,\"imp_kwh\":3.0,\"exp_kwh\":4.0},\"checklist_answers\":{\"solar_module_clean\":{\"value\":\"YES\"}},\"media\":[{\"item_key\":\"net_meter_readings\",\"object_path\":\"media/p1d/${wo2_id}/net-meter.jpg\",\"content_type\":\"image/jpeg\",\"size_bytes\":1000}],\"tech_signature\":{\"signer_name\":\"Tech One\",\"signer_phone\":\"+15550000000\",\"signature_object_path\":\"signatures/${wo2_id}/tech.png\"}}"
wo2_submit_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/submit" "${wo2_submit_payload}" "${wo2_submit_out}")"
run_test "P1D submit workorder 2" "200" "${wo2_submit_code}"

wo2_report_out="${REPORT_DIR}/p1d_wo2_report_data.json"
wo2_report_code="$(api_call "GET" "${SERVICE_URL}/workorders/${wo2_id}/report-data" "" "${wo2_report_out}")"
run_test "P1D report-data workorder 2" "200" "${wo2_report_code}"
run_test "P1D generation total delta visit" "200|200.0" "$(json_value generation_total_kwh "${wo2_report_out}")"

wo2_sync_out="${REPORT_DIR}/p1d_wo2_report_sync.json"
wo2_sync_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo2_id}/generate-report" "{\"is_final\":false,\"idempotency_key\":\"p1d-cloud-${ts}\"}" "${wo2_sync_out}")"
run_test "P1D generate report sync" "200" "${wo2_sync_code}"

write_reports \
  "Phase 1D Post-Deploy API Summary" \
  "${SERVICE_URL}" \
  "${REPORT_BRANCH:-manual}" \
  "${BUILD_ID:-unknown}" \
  "${SUMMARY_FILE}" \
  "${JUNIT_FILE}" \
  "${EXIT_FILE}"

exit 0
