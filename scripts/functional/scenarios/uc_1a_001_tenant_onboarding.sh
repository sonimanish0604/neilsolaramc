#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1a_001_tenant_onboarding() {
  local prefix="UC-1A-001"
  local ts
  ts="$(date +%s)"

  local tenant_name="func-tenant-${REPORT_BRANCH}-${BUILD_ID:-manual}-${ts}"
  local tenant_payload
  tenant_payload="{\"name\":\"${tenant_name}\",\"plan_code\":\"TRIAL\",\"status\":\"ACTIVE\"}"

  local tenant_out="${REPORT_DIR}/uc_1a_001_tenant.json"
  local tenant_code
  tenant_code="$(http_code POST "${SERVICE_URL}/admin/tenants" "${tenant_payload}" "${tenant_out}" "true")"
  run_test "${prefix} create tenant" "200" "${tenant_code}"

  UC_TENANT_ID="$(json_field id "${tenant_out}")"
  if [[ -z "${UC_TENANT_ID}" ]]; then
    UC_TENANT_ID="00000000-0000-0000-0000-000000000000"
  fi

  local user_uid="func-owner-${REPORT_BRANCH}-${BUILD_ID:-manual}-${ts}"
  local user_payload
  user_payload="{\"tenant_id\":\"${UC_TENANT_ID}\",\"firebase_uid\":\"${user_uid}\",\"name\":\"Functional Owner\",\"email\":\"owner@example.com\",\"status\":\"ACTIVE\"}"

  local user_out="${REPORT_DIR}/uc_1a_001_user.json"
  local user_code
  user_code="$(http_code POST "${SERVICE_URL}/admin/users" "${user_payload}" "${user_out}" "true")"
  run_test "${prefix} create owner user" "200" "${user_code}"

  UC_OWNER_USER_ID="$(json_field id "${user_out}")"
  if [[ -z "${UC_OWNER_USER_ID}" ]]; then
    UC_OWNER_USER_ID="00000000-0000-0000-0000-000000000000"
  fi

  local role_code
  role_code="$(http_code POST "${SERVICE_URL}/admin/users/${UC_OWNER_USER_ID}/roles" '{"role":"OWNER"}' "${REPORT_DIR}/uc_1a_001_role.json" "true")"
  run_test "${prefix} assign OWNER role" "200|409" "${role_code}"

  local dup_code
  dup_code="$(http_code POST "${SERVICE_URL}/admin/tenants" "${tenant_payload}" "${REPORT_DIR}/uc_1a_001_tenant_dup.json" "true")"
  run_test "${prefix} duplicate tenant rejected" "409" "${dup_code}"
}

