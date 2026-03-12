#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source "${ROOT_DIR}/scripts/functional/lib/common.sh"

SERVICE_URL="${SERVICE_URL:?SERVICE_URL is required}"
REPORT_DIR="${REPORT_DIR:-/workspace/reports}"
FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-}"
FUNCTIONAL_ASSIGNED_TECH_USER_ID="${FUNCTIONAL_ASSIGNED_TECH_USER_ID:-}"
SUMMARY_FILE="${SUMMARY_FILE:-${REPORT_DIR}/phase1e_post_deploy_summary.md}"
JUNIT_FILE="${JUNIT_FILE:-${REPORT_DIR}/phase1e_post_deploy_junit.xml}"
EXIT_FILE="${EXIT_FILE:-${REPORT_DIR}/phase1e_post_deploy_exit_code.txt}"

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
  run_skip "P1E auth token present" "FUNCTIONAL_BEARER_TOKEN not provided"
  write_reports \
    "Phase 1E Post-Deploy API Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH:-manual}" \
    "${BUILD_ID:-unknown}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  exit 0
fi

if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID}" ]]; then
  run_skip "P1E assigned tech user id present" "FUNCTIONAL_ASSIGNED_TECH_USER_ID not provided"
  write_reports \
    "Phase 1E Post-Deploy API Summary" \
    "${SERVICE_URL}" \
    "${REPORT_BRANCH:-manual}" \
    "${BUILD_ID:-unknown}" \
    "${SUMMARY_FILE}" \
    "${JUNIT_FILE}" \
    "${EXIT_FILE}"
  exit 0
fi

ts="$(date +%s)"
scheduled_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
customer_name="P1E Cloud Customer ${ts}"

customer_out="${REPORT_DIR}/p1e_customer.json"
customer_code="$(api_call "POST" "${SERVICE_URL}/customers" "{\"name\":\"${customer_name}\",\"address\":\"P1E cloud\",\"status\":\"ACTIVE\"}" "${customer_out}")"
run_test "P1E seed create customer" "200" "${customer_code}"
customer_id="$(json_value id "${customer_out}")"

site_invalid_out="${REPORT_DIR}/p1e_site_invalid_coords.json"
site_invalid_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"P1E Invalid Site ${ts}\",\"address\":\"P1E cloud\",\"site_latitude\":26.7980,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Cloud Supervisor\",\"site_supervisor_phone\":\"+15550110011\",\"site_supervisor_email\":\"p1e.invalid@example.com\"}"
site_invalid_code="$(api_call "POST" "${SERVICE_URL}/sites" "${site_invalid_payload}" "${site_invalid_out}")"
run_test "P1E reject site with partial coordinate pair" "400|422" "${site_invalid_code}"

site_no_geo_out="${REPORT_DIR}/p1e_site_no_geo.json"
site_no_geo_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"P1E Site No Geo ${ts}\",\"address\":\"P1E cloud\",\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Cloud Supervisor\",\"site_supervisor_phone\":\"+15550110011\",\"site_supervisor_email\":\"p1e.nogeo@example.com\"}"
site_no_geo_code="$(api_call "POST" "${SERVICE_URL}/sites" "${site_no_geo_payload}" "${site_no_geo_out}")"
run_test "P1E create site without coordinates" "200" "${site_no_geo_code}"
site_no_geo_id="$(json_value id "${site_no_geo_out}")"

site_geo_out="${REPORT_DIR}/p1e_site_geo.json"
site_geo_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"P1E Site Geo ${ts}\",\"address\":\"P1E cloud\",\"site_latitude\":26.7980,\"site_longitude\":80.9020,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Cloud Supervisor\",\"site_supervisor_phone\":\"+15550110012\",\"site_supervisor_email\":\"p1e.geo@example.com\"}"
site_geo_code="$(api_call "POST" "${SERVICE_URL}/sites" "${site_geo_payload}" "${site_geo_out}")"
run_test "P1E create site with coordinates" "200" "${site_geo_code}"
site_geo_id="$(json_value id "${site_geo_out}")"

site_patch_invalid_out="${REPORT_DIR}/p1e_site_patch_invalid_coords.json"
site_patch_invalid_code="$(api_call "PATCH" "${SERVICE_URL}/sites/${site_geo_id}" "{\"site_longitude\":80.9021}" "${site_patch_invalid_out}")"
run_test "P1E reject site patch with partial coordinate pair" "400|422" "${site_patch_invalid_code}"

inv_no_geo_out="${REPORT_DIR}/p1e_inv_no_geo.json"
inv_no_geo_code="$(api_call "POST" "${SERVICE_URL}/sites/${site_no_geo_id}/inverters" "{\"inverter_code\":\"INV-NOGEO\",\"display_name\":\"Inverter NoGeo\",\"capacity_kw\":25,\"is_active\":true}" "${inv_no_geo_out}")"
run_test "P1E create inverter for no-geo site" "200" "${inv_no_geo_code}"
inv_no_geo_id="$(json_value id "${inv_no_geo_out}")"

inv_geo_out="${REPORT_DIR}/p1e_inv_geo.json"
inv_geo_code="$(api_call "POST" "${SERVICE_URL}/sites/${site_geo_id}/inverters" "{\"inverter_code\":\"INV-GEO\",\"display_name\":\"Inverter Geo\",\"capacity_kw\":25,\"is_active\":true}" "${inv_geo_out}")"
run_test "P1E create inverter for geo site" "200" "${inv_geo_code}"
inv_geo_id="$(json_value id "${inv_geo_out}")"

wo_no_geo_out="${REPORT_DIR}/p1e_wo_no_geo.json"
wo_no_geo_payload="{\"site_id\":\"${site_no_geo_id}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${scheduled_at}\"}"
wo_no_geo_code="$(api_call "POST" "${SERVICE_URL}/workorders" "${wo_no_geo_payload}" "${wo_no_geo_out}")"
run_test "P1E create workorder for no-geo site" "200" "${wo_no_geo_code}"
wo_no_geo_id="$(json_value id "${wo_no_geo_out}")"

wo_geo_out="${REPORT_DIR}/p1e_wo_geo.json"
wo_geo_payload="{\"site_id\":\"${site_geo_id}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${scheduled_at}\"}"
wo_geo_code="$(api_call "POST" "${SERVICE_URL}/workorders" "${wo_geo_payload}" "${wo_geo_out}")"
run_test "P1E create workorder for geo site" "200" "${wo_geo_code}"
wo_geo_id="$(json_value id "${wo_geo_out}")"

cap_no_geo_out="${REPORT_DIR}/p1e_cap_no_geo.json"
cap_no_geo_payload="{\"inverter_id\":\"${inv_no_geo_id}\",\"current_reading_kwh\":1000.0,\"device_latitude\":26.7981,\"device_longitude\":80.9021,\"device_accuracy_meters\":10.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"geo test no site coords\",\"photo_object_path\":\"media/p1e/${wo_no_geo_id}/inv.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1024}"
cap_no_geo_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo_no_geo_id}/inverter-readings" "${cap_no_geo_payload}" "${cap_no_geo_out}")"
run_test "P1E capture no-geo site reading" "200" "${cap_no_geo_code}"
run_test "P1E geo status geo_unverified when site coords missing" "geo_unverified" "$(json_value geo_validation_status "${cap_no_geo_out}")"

cap_missing_device_out="${REPORT_DIR}/p1e_cap_missing_device.json"
cap_missing_device_payload="{\"inverter_id\":\"${inv_geo_id}\",\"current_reading_kwh\":1100.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"geo test missing device\",\"photo_object_path\":\"media/p1e/${wo_geo_id}/inv-missing-device.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1025}"
cap_missing_device_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo_geo_id}/inverter-readings" "${cap_missing_device_payload}" "${cap_missing_device_out}")"
run_test "P1E capture reading missing device location" "200" "${cap_missing_device_code}"
run_test "P1E geo status missing_device_location" "missing_device_location" "$(json_value geo_validation_status "${cap_missing_device_out}")"

cap_low_accuracy_out="${REPORT_DIR}/p1e_cap_low_accuracy.json"
cap_low_accuracy_payload="{\"inverter_id\":\"${inv_geo_id}\",\"current_reading_kwh\":1101.0,\"device_latitude\":26.7981,\"device_longitude\":80.9021,\"device_accuracy_meters\":150.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"geo test low accuracy\",\"photo_object_path\":\"media/p1e/${wo_geo_id}/inv-low-accuracy.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1026}"
cap_low_accuracy_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo_geo_id}/inverter-readings" "${cap_low_accuracy_payload}" "${cap_low_accuracy_out}")"
run_test "P1E capture reading low accuracy" "200" "${cap_low_accuracy_code}"
run_test "P1E geo status low_accuracy" "low_accuracy" "$(json_value geo_validation_status "${cap_low_accuracy_out}")"

cap_outside_out="${REPORT_DIR}/p1e_cap_outside.json"
cap_outside_payload="{\"inverter_id\":\"${inv_geo_id}\",\"current_reading_kwh\":1102.0,\"device_latitude\":26.8100,\"device_longitude\":80.9020,\"device_accuracy_meters\":10.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"geo test outside\",\"photo_object_path\":\"media/p1e/${wo_geo_id}/inv-outside.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1027}"
cap_outside_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo_geo_id}/inverter-readings" "${cap_outside_payload}" "${cap_outside_out}")"
run_test "P1E capture reading outside boundary" "200" "${cap_outside_code}"
run_test "P1E geo status outside_site_boundary" "outside_site_boundary" "$(json_value geo_validation_status "${cap_outside_out}")"
outside_distance="$(json_value distance_to_site_meters "${cap_outside_out}")"
run_test "P1E outside distance present" "YES" "$([[ -n "${outside_distance}" ]] && echo YES || echo NO)"

cap_verified_out="${REPORT_DIR}/p1e_cap_verified.json"
cap_verified_payload="{\"inverter_id\":\"${inv_geo_id}\",\"current_reading_kwh\":1103.0,\"device_latitude\":26.7981,\"device_longitude\":80.9021,\"device_accuracy_meters\":10.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"geo test verified\",\"photo_object_path\":\"media/p1e/${wo_geo_id}/inv-verified.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":1028}"
cap_verified_code="$(api_call "POST" "${SERVICE_URL}/workorders/${wo_geo_id}/inverter-readings" "${cap_verified_payload}" "${cap_verified_out}")"
run_test "P1E capture reading verified" "200" "${cap_verified_code}"
run_test "P1E geo status verified" "verified" "$(json_value geo_validation_status "${cap_verified_out}")"
verified_distance="$(json_value distance_to_site_meters "${cap_verified_out}")"
run_test "P1E verified distance present" "YES" "$([[ -n "${verified_distance}" ]] && echo YES || echo NO)"

write_reports \
  "Phase 1E Post-Deploy API Summary" \
  "${SERVICE_URL}" \
  "${REPORT_BRANCH:-manual}" \
  "${BUILD_ID:-unknown}" \
  "${SUMMARY_FILE}" \
  "${JUNIT_FILE}" \
  "${EXIT_FILE}"

exit 0
