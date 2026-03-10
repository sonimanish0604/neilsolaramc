#!/usr/bin/env bash
set -euo pipefail

scenario_uc_1b_002_notification_email_smoke() {
  local prefix="UC-1B-002"
  local email_to="${FUNCTIONAL_PHASE1B_EMAIL_TO:-}"

  if [[ -z "${email_to}" ]]; then
    run_skip "${prefix} send notification test email" "FUNCTIONAL_PHASE1B_EMAIL_TO not provided"
    return 0
  fi

  local selector="${FUNCTIONAL_PHASE1B_DOMAIN_SELECTOR:-1}"
  local from_email="${FUNCTIONAL_PHASE1B_EMAIL_FROM:-}"
  local subject="${FUNCTIONAL_PHASE1B_EMAIL_SUBJECT:-Phase1B notification smoke $(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  local text="${FUNCTIONAL_PHASE1B_EMAIL_TEXT:-Phase1B notification smoke message}"

  local payload
  payload="$(python3 - "${email_to}" "${subject}" "${text}" "${selector}" "${from_email}" <<'PY'
import json
import sys

email_to, subject, text, selector_raw, from_email = sys.argv[1:6]
payload = {
    "to": email_to,
    "subject": subject,
    "text": text,
    "domain_selector": int(selector_raw),
}
if from_email:
    payload["from_email"] = from_email
print(json.dumps(payload))
PY
)"

  local out_file="${REPORT_DIR}/uc_1b_002_notification_email_smoke.json"
  local code
  code="$(http_code POST "${SERVICE_URL}/notifications/trysendemail" "${payload}" "${out_file}" "true")"
  run_test "${prefix} send notification test email" "200" "${code}"

  if [[ "${code}" == "200" ]]; then
    local provider used_selector
    provider="$(json_field provider "${out_file}")"
    used_selector="$(json_field used_domain_selector "${out_file}")"
    run_test "${prefix} provider returned" "MAILGUN|TWILIO|SMTP" "${provider}"
    run_test "${prefix} domain selector applied" "${selector}" "${used_selector}"
  fi
}
