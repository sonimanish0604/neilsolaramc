#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1d_002_visit1_capture_baseline() {
  local prefix="UC-1D-002"

  if [[ "${P1D_SETUP_OK:-false}" != "true" ]]; then
    run_skip "${prefix} visit 1 baseline flow" "UC-1D-001 setup did not complete"
    return
  fi

  local cap1_out="${REPORT_DIR}/uc_1d_002_wo1_capture_inv1.json"
  local cap1_payload
  cap1_payload="{\"inverter_id\":\"${P1D_INV1_ID}\",\"current_reading_kwh\":600.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"visit1 baseline\",\"photo_object_path\":\"media/functional/${P1D_WO1_ID}/inv1.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":12001}"
  local cap1_code
  cap1_code="$(api_call POST "${SERVICE_URL}/workorders/${P1D_WO1_ID}/inverter-readings" "${cap1_payload}" "${cap1_out}")"
  run_test "${prefix} capture INV-01 baseline 600" "200" "${cap1_code}"
  run_test "${prefix} INV-01 baseline flag true" "true|True" "$(json_path is_baseline "${cap1_out}")"

  local cap2_out="${REPORT_DIR}/uc_1d_002_wo1_capture_inv2.json"
  local cap2_payload
  cap2_payload="{\"inverter_id\":\"${P1D_INV2_ID}\",\"current_reading_kwh\":400.0,\"operational_status\":\"OPERATIONAL\",\"remarks\":\"visit1 baseline\",\"photo_object_path\":\"media/functional/${P1D_WO1_ID}/inv2.jpg\",\"photo_content_type\":\"image/jpeg\",\"photo_size_bytes\":12002}"
  local cap2_code
  cap2_code="$(api_call POST "${SERVICE_URL}/workorders/${P1D_WO1_ID}/inverter-readings" "${cap2_payload}" "${cap2_out}")"
  run_test "${prefix} capture INV-02 baseline 400" "200" "${cap2_code}"
  run_test "${prefix} INV-02 baseline flag true" "true|True" "$(json_path is_baseline "${cap2_out}")"

  local submit_out="${REPORT_DIR}/uc_1d_002_wo1_submit.json"
  local submit_payload
  submit_payload="{\"visit_status\":\"SATISFACTORY\",\"summary_notes\":\"phase1d functional visit1 baseline total=1000\",\"inverter_readings\":[],\"net_meter\":{\"net_kwh\":1000.0,\"imp_kwh\":0.0,\"exp_kwh\":0.0},\"checklist_answers\":{\"solar_module_clean\":{\"value\":\"YES\"}},\"media\":[{\"item_key\":\"net_meter_readings\",\"object_path\":\"media/functional/${P1D_WO1_ID}/net-meter.jpg\",\"content_type\":\"image/jpeg\",\"size_bytes\":13000}],\"tech_signature\":{\"signer_name\":\"Functional Tech\",\"signer_phone\":\"+15550000000\",\"signature_object_path\":\"signatures/${P1D_WO1_ID}/tech.png\"}}"
  local submit_code
  submit_code="$(api_call POST "${SERVICE_URL}/workorders/${P1D_WO1_ID}/submit" "${submit_payload}" "${submit_out}")"
  run_test "${prefix} submit workorder 1" "200" "${submit_code}"

  local send_approval_out="${REPORT_DIR}/uc_1d_002_wo1_send_approval.json"
  local send_approval_code
  send_approval_code="$(api_call POST "${SERVICE_URL}/workorders/${P1D_WO1_ID}/send-approval" "{\"channel\":\"EMAIL\"}" "${send_approval_out}")"
  run_test "${prefix} send approval workorder 1" "200" "${send_approval_code}"
  local approval_token
  approval_token="$(json_path approval_token "${send_approval_out}")"

  local sign_out="${REPORT_DIR}/uc_1d_002_wo1_customer_sign.json"
  local sign_payload
  sign_payload="{\"signer_name\":\"Functional Supervisor\",\"signer_phone\":\"+15550111111\",\"signature_object_path\":\"signatures/${P1D_WO1_ID}/customer.png\"}"
  local sign_code
  sign_code="$(http_code POST "${SERVICE_URL}/approve/${approval_token}/sign" "${sign_payload}" "${sign_out}")"
  run_test "${prefix} customer sign workorder 1" "200" "${sign_code}"
  run_test "${prefix} customer sign status" "SIGNED|SIGNED_REPORT_PENDING" "$(json_path status "${sign_out}")"

  local report_out="${REPORT_DIR}/uc_1d_002_wo1_report_data.json"
  local report_code
  report_code="$(api_call GET "${SERVICE_URL}/workorders/${P1D_WO1_ID}/report-data" "" "${report_out}")"
  run_test "${prefix} report-data workorder 1" "200" "${report_code}"
  run_test "${prefix} visit1 generation total = 0 baseline" "0|0.0" "$(json_path generation_total_kwh "${report_out}")"
}
