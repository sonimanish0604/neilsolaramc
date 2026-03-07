#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1a_002_customer_site_flow() {
  local prefix="UC-1A-002"

  if [[ -z "${FUNCTIONAL_BEARER_TOKEN:-}" ]]; then
    run_skip "${prefix} create customer" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} duplicate customer rejected" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} list customers" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} create site" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} duplicate site rejected" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} list sites by customer" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} update customer" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} update site" "FUNCTIONAL_BEARER_TOKEN not provided"
    run_skip "${prefix} update missing site returns 404" "FUNCTIONAL_BEARER_TOKEN not provided"
    return 0
  fi

  local customer_out="${REPORT_DIR}/uc_1a_002_customer.json"
  local customer_code
  customer_code="$(http_code POST "${SERVICE_URL}/customers" '{"name":"Functional Customer","address":"Mumbai","status":"ACTIVE"}' "${customer_out}" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} create customer" "200" "${customer_code}"

  local customer_id
  customer_id="$(json_field id "${customer_out}")"
  if [[ -z "${customer_id}" ]]; then
    customer_id="00000000-0000-0000-0000-000000000000"
  fi

  local customer_dup_code
  customer_dup_code="$(http_code POST "${SERVICE_URL}/customers" '{"name":"Functional Customer","address":"Mumbai","status":"ACTIVE"}' "${REPORT_DIR}/uc_1a_002_customer_dup.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} duplicate customer rejected" "409" "${customer_dup_code}"

  local customers_list_code
  customers_list_code="$(http_code GET "${SERVICE_URL}/customers" "" "${REPORT_DIR}/uc_1a_002_customers_list.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} list customers" "200" "${customers_list_code}"

  local site_payload
  site_payload="{\"customer_id\":\"${customer_id}\",\"site_name\":\"Functional Site\",\"address\":\"Andheri\",\"capacity_kw\":10.5,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Supervisor\",\"site_supervisor_phone\":\"9999999999\"}"
  local site_out="${REPORT_DIR}/uc_1a_002_site.json"
  local site_code
  site_code="$(http_code POST "${SERVICE_URL}/sites" "${site_payload}" "${site_out}" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} create site" "200" "${site_code}"

  local site_id
  site_id="$(json_field id "${site_out}")"
  if [[ -z "${site_id}" ]]; then
    site_id="00000000-0000-0000-0000-000000000000"
  fi

  local site_dup_code
  site_dup_code="$(http_code POST "${SERVICE_URL}/sites" "${site_payload}" "${REPORT_DIR}/uc_1a_002_site_dup.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} duplicate site rejected" "409" "${site_dup_code}"

  local sites_list_code
  sites_list_code="$(http_code GET "${SERVICE_URL}/sites?customer_id=${customer_id}" "" "${REPORT_DIR}/uc_1a_002_sites_list.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} list sites by customer" "200" "${sites_list_code}"

  local customer_update_code
  customer_update_code="$(http_code PATCH "${SERVICE_URL}/customers/${customer_id}" '{"address":"Pune","status":"INACTIVE"}' "${REPORT_DIR}/uc_1a_002_customer_upd.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} update customer" "200" "${customer_update_code}"

  local site_update_code
  site_update_code="$(http_code PATCH "${SERVICE_URL}/sites/${site_id}" '{"capacity_kw":12.0,"status":"INACTIVE"}' "${REPORT_DIR}/uc_1a_002_site_upd.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} update site" "200" "${site_update_code}"

  local missing_site_code
  missing_site_code="$(http_code PATCH "${SERVICE_URL}/sites/00000000-0000-0000-0000-000000000001" '{"status":"ACTIVE"}' "${REPORT_DIR}/uc_1a_002_site_missing.json" "false" "${FUNCTIONAL_BEARER_TOKEN}")"
  run_test "${prefix} update missing site returns 404" "404" "${missing_site_code}"
}

