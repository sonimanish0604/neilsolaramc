#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1d_001_setup_site_inventory() {
  local prefix="UC-1D-001"
  local ts
  ts="$(date +%s)"

  local customer_name="Phase1D Functional Customer ${REPORT_BRANCH:-local}-${BUILD_ID:-manual}-${ts}"
  local site_name="Phase1D Functional Site ${REPORT_BRANCH:-local}-${BUILD_ID:-manual}-${ts}"

  if [[ -z "${FUNCTIONAL_ASSIGNED_TECH_USER_ID:-}" ]]; then
    run_skip "${prefix} assigned tech user configured" "FUNCTIONAL_ASSIGNED_TECH_USER_ID not set"
    P1D_SETUP_OK="false"
    return
  fi

  if [[ -n "${ADMIN_KEY:-}" ]]; then
    local role
    for role in OWNER SUPERVISOR TECH; do
      local role_out="${REPORT_DIR}/uc_1d_001_assign_${role,,}_role.json"
      local role_code
      role_code="$(http_code POST "${SERVICE_URL}/admin/users/${FUNCTIONAL_ASSIGNED_TECH_USER_ID}/roles" "{\"role\":\"${role}\"}" "${role_out}" "true")"
      run_test "${prefix} ensure ${role} role" "200|409" "${role_code}"
    done
  else
    run_skip "${prefix} role bootstrap" "ADMIN_KEY not provided"
  fi

  local customer_out="${REPORT_DIR}/uc_1d_001_customer.json"
  local customer_code
  customer_code="$(api_call POST "${SERVICE_URL}/customers" "{\"name\":\"${customer_name}\",\"address\":\"Phase1D functional test\",\"status\":\"ACTIVE\"}" "${customer_out}")"
  run_test "${prefix} create customer" "200" "${customer_code}"
  P1D_CUSTOMER_ID="$(json_path id "${customer_out}")"

  local site_out="${REPORT_DIR}/uc_1d_001_site.json"
  local site_payload
  site_payload="{\"customer_id\":\"${P1D_CUSTOMER_ID}\",\"site_name\":\"${site_name}\",\"address\":\"Phase1D functional test\",\"capacity_kw\":300,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Functional Supervisor\",\"site_supervisor_phone\":\"+15550111111\",\"site_supervisor_email\":\"phase1d.functional.supervisor@example.com\"}"
  local site_code
  site_code="$(api_call POST "${SERVICE_URL}/sites" "${site_payload}" "${site_out}")"
  run_test "${prefix} create site" "200" "${site_code}"
  P1D_SITE_ID="$(json_path id "${site_out}")"

  local inv1_out="${REPORT_DIR}/uc_1d_001_inverter_1.json"
  local inv1_code
  inv1_code="$(api_call POST "${SERVICE_URL}/sites/${P1D_SITE_ID}/inverters" "{\"inverter_code\":\"INV-01\",\"display_name\":\"Inverter 01\",\"capacity_kw\":25,\"is_active\":true}" "${inv1_out}")"
  run_test "${prefix} create inverter INV-01" "200" "${inv1_code}"
  P1D_INV1_ID="$(json_path id "${inv1_out}")"

  local inv2_out="${REPORT_DIR}/uc_1d_001_inverter_2.json"
  local inv2_code
  inv2_code="$(api_call POST "${SERVICE_URL}/sites/${P1D_SITE_ID}/inverters" "{\"inverter_code\":\"INV-02\",\"display_name\":\"Inverter 02\",\"capacity_kw\":25,\"is_active\":true}" "${inv2_out}")"
  run_test "${prefix} create inverter INV-02" "200" "${inv2_code}"
  P1D_INV2_ID="$(json_path id "${inv2_out}")"

  local wo1_out="${REPORT_DIR}/uc_1d_001_workorder_1.json"
  local wo1_payload
  wo1_payload="{\"site_id\":\"${P1D_SITE_ID}\",\"assigned_tech_user_id\":\"${FUNCTIONAL_ASSIGNED_TECH_USER_ID}\",\"scheduled_at\":\"${P1D_VISIT1_SCHEDULED_AT}\"}"
  local wo1_code
  wo1_code="$(api_call POST "${SERVICE_URL}/workorders" "${wo1_payload}" "${wo1_out}")"
  run_test "${prefix} create workorder 1 (${P1D_VISIT1_SCHEDULED_AT})" "200" "${wo1_code}"
  P1D_WO1_ID="$(json_path id "${wo1_out}")"

  local wo1_inv_out="${REPORT_DIR}/uc_1d_001_workorder_1_inverters.json"
  local wo1_inv_code
  wo1_inv_code="$(api_call GET "${SERVICE_URL}/workorders/${P1D_WO1_ID}/inverters" "" "${wo1_inv_out}")"
  run_test "${prefix} list workorder 1 inverters" "200" "${wo1_inv_code}"
  run_test "${prefix} workorder inverter count >= 2" "YES" "$([[ "$(json_path inverters.1.inverter_code "${wo1_inv_out}")" == "INV-02" ]] && echo YES || echo NO)"

  P1D_SETUP_OK="true"
}
