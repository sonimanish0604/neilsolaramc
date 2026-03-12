#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1d_003_visit2_capture_delta() {
  local prefix="UC-1D-003"

  if [[ "${P1D_SETUP_OK:-false}" != "true" ]]; then
    run_skip "${prefix} visit 2 delta flow" "UC-1D-001 setup did not complete"
    return
  fi

  local wo2_out="${REPORT_DIR}/uc_1d_003_workorder_2.json"
  local wo2_payload
  wo2_payload="{\"site_id\":\"${P1D_SITE_ID}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${P1D_VISIT2_SCHEDULED_AT}\"}"
  local wo2_code
  wo2_code="$(api_call POST "${SERVICE_URL}/workorders" "${wo2_payload}" "${wo2_out}")"
  run_test "${prefix} create workorder 2 (${P1D_VISIT2_SCHEDULED_AT})" "200" "${wo2_code}"
  local wo2_id
  wo2_id="$(json_path id "${wo2_out}")"

  local cap1_out="${REPORT_DIR}/uc_1d_003_wo2_capture_inv1.json"
  local cap1_payload
  cap1_payload="{\"inverter_id\":\"${P1D_INV1_ID}\",\"current_reading_kwh\":1200.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"visit2 reading\",\"photo_object_path\":\"media/functional/${wo2_id}/inv1.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":22001}"
  local cap1_code
  cap1_code="$(api_call POST "${SERVICE_URL}/workorders/${wo2_id}/inverter-readings" "${cap1_payload}" "${cap1_out}")"
  run_test "${prefix} capture INV-01 visit2 reading 1200" "200" "${cap1_code}"
  run_test "${prefix} INV-01 delta = 600" "600|600.0" "$(json_path generation_delta_kwh "${cap1_out}")"

  local cap2_out="${REPORT_DIR}/uc_1d_003_wo2_capture_inv2.json"
  local cap2_payload
  cap2_payload="{\"inverter_id\":\"${P1D_INV2_ID}\",\"current_reading_kwh\":800.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"visit2 reading\",\"photo_object_path\":\"media/functional/${wo2_id}/inv2.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":22002}"
  local cap2_code
  cap2_code="$(api_call POST "${SERVICE_URL}/workorders/${wo2_id}/inverter-readings" "${cap2_payload}" "${cap2_out}")"
  run_test "${prefix} capture INV-02 visit2 reading 800" "200" "${cap2_code}"
  run_test "${prefix} INV-02 delta = 400" "400|400.0" "$(json_path generation_delta_kwh "${cap2_out}")"

  local submit_out="${REPORT_DIR}/uc_1d_003_wo2_submit.json"
  local submit_payload
  submit_payload="{\"visit_status\":\"SATISFACTORY\",\"summary_notes\":\"phase1d functional visit2 total=2000 delta=1000\",\"inverter_readings\":[],\"net_meter\":{\"net_kwh\":2000.0,\"imp_kwh\":0.0,\"exp_kwh\":0.0},\"checklist_answers\":{\"solar_module_clean\":{\"value\":\"YES\"}},\"media\":[{\"item_key\":\"net_meter_readings\",\"object_path\":\"media/functional/${wo2_id}/net-meter.jpg\",\"content_type\":\"image/jpeg\",\"size_bytes\":23000}],\"tech_signature\":{\"signer_name\":\"Functional Tech\",\"signer_phone\":\"+15550000000\",\"signature_object_path\":\"signatures/${wo2_id}/tech.png\"}}"
  local submit_code
  submit_code="$(api_call POST "${SERVICE_URL}/workorders/${wo2_id}/submit" "${submit_payload}" "${submit_out}")"
  run_test "${prefix} submit workorder 2" "200" "${submit_code}"

  local report_out="${REPORT_DIR}/uc_1d_003_wo2_report_data.json"
  local report_code
  report_code="$(api_call GET "${SERVICE_URL}/workorders/${wo2_id}/report-data" "" "${report_out}")"
  run_test "${prefix} report-data workorder 2" "200" "${report_code}"
  run_test "${prefix} visit2 generation total = 1000" "1000|1000.0" "$(json_path generation_total_kwh "${report_out}")"
}
