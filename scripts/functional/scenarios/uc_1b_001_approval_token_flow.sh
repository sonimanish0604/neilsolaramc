#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1b_001_approval_token_flow() {
  local prefix="UC-1B-001"
  local token="${FUNCTIONAL_APPROVAL_TOKEN:-}"

  if [[ -z "${token}" ]]; then
    run_skip "${prefix} open approval link" "FUNCTIONAL_APPROVAL_TOKEN not provided"
    run_skip "${prefix} submit customer signature" "FUNCTIONAL_APPROVAL_TOKEN not provided"
    run_skip "${prefix} reject token reuse" "FUNCTIONAL_APPROVAL_TOKEN not provided"
    return 0
  fi

  local open_out="${REPORT_DIR}/uc_1b_001_open.json"
  local open_code
  open_code="$(http_code GET "${SERVICE_URL}/approve/${token}" "" "${open_out}")"
  run_test "${prefix} open approval link" "200" "${open_code}"

  local signer_name="${FUNCTIONAL_CUSTOMER_SIGNER_NAME:-Functional Customer}"
  local signer_phone="${FUNCTIONAL_CUSTOMER_SIGNER_PHONE:-+919999999999}"
  local signature_path="${FUNCTIONAL_CUSTOMER_SIGNATURE_OBJECT_PATH:-signatures/customer-signature.png}"
  local sign_payload
  sign_payload="{\"signer_name\":\"${signer_name}\",\"signer_phone\":\"${signer_phone}\",\"signature_object_path\":\"${signature_path}\"}"

  local sign_out="${REPORT_DIR}/uc_1b_001_sign.json"
  local sign_code
  sign_code="$(http_code POST "${SERVICE_URL}/approve/${token}/sign" "${sign_payload}" "${sign_out}")"
  run_test "${prefix} submit customer signature" "200" "${sign_code}"

  local reuse_out="${REPORT_DIR}/uc_1b_001_reuse.json"
  local reuse_code
  reuse_code="$(http_code POST "${SERVICE_URL}/approve/${token}/sign" "${sign_payload}" "${reuse_out}")"
  run_test "${prefix} reject token reuse" "409" "${reuse_code}"
}
