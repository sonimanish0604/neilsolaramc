#!/usr/bin/env bash
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-root}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required"
  exit 1
fi

echo "[vault-seed] Using VAULT_ADDR=${VAULT_ADDR}"

seed_v2_secret() {
  local path="$1"
  local json="$2"
  curl -sS -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "{\"data\": ${json}}" \
    "${VAULT_ADDR}/v1/secret/data/${path}" >/dev/null
  echo "[vault-seed] upserted secret/${path}"
}

seed_v2_secret "neilsolar/local/notification" '{"mailgun_api_key":"replace-me","sendgrid_api_key":"replace-me"}'
seed_v2_secret "neilsolar/local/twilio" '{"auth_token":"replace-me"}'
seed_v2_secret "neilsolar/local/smtp" '{"password":"replace-me"}'

echo "[vault-seed] done"
