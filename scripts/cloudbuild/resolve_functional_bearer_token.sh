#!/usr/bin/env bash
set -euo pipefail

TOKEN_FILE="${TOKEN_FILE:-/workspace/.functional_bearer_token}"

RUN_STATEFUL_POST_DEPLOY_TESTS="${RUN_STATEFUL_POST_DEPLOY_TESTS:-false}"
RUN_PHASE1B_APPROVAL_SCENARIO="${RUN_PHASE1B_APPROVAL_SCENARIO:-false}"
RUN_PHASE1B_NOTIFICATION_SMOKE="${RUN_PHASE1B_NOTIFICATION_SMOKE:-false}"
RUN_PHASE1C_POST_DEPLOY_TESTS="${RUN_PHASE1C_POST_DEPLOY_TESTS:-false}"
RUN_PHASE1D_POST_DEPLOY_TESTS="${RUN_PHASE1D_POST_DEPLOY_TESTS:-false}"
RUN_PHASE1E_POST_DEPLOY_TESTS="${RUN_PHASE1E_POST_DEPLOY_TESTS:-false}"

FUNCTIONAL_BEARER_TOKEN="${FUNCTIONAL_BEARER_TOKEN:-}"
FUNCTIONAL_FIREBASE_API_KEY_SECRET="${FUNCTIONAL_FIREBASE_API_KEY_SECRET:-}"
FUNCTIONAL_TEST_EMAIL_SECRET="${FUNCTIONAL_TEST_EMAIL_SECRET:-}"
FUNCTIONAL_TEST_PASSWORD_SECRET="${FUNCTIONAL_TEST_PASSWORD_SECRET:-}"

requires_token=false
for flag in \
  "${RUN_STATEFUL_POST_DEPLOY_TESTS}" \
  "${RUN_PHASE1B_APPROVAL_SCENARIO}" \
  "${RUN_PHASE1B_NOTIFICATION_SMOKE}" \
  "${RUN_PHASE1C_POST_DEPLOY_TESTS}" \
  "${RUN_PHASE1D_POST_DEPLOY_TESTS}" \
  "${RUN_PHASE1E_POST_DEPLOY_TESTS}"; do
  if [[ "${flag}" == "true" ]]; then
    requires_token=true
    break
  fi
done

if [[ -n "${FUNCTIONAL_BEARER_TOKEN}" ]]; then
  umask 077
  printf '%s' "${FUNCTIONAL_BEARER_TOKEN}" > "${TOKEN_FILE}"
  echo "Using _FUNCTIONAL_BEARER_TOKEN override for functional API tests."
  exit 0
fi

if [[ "${requires_token}" != "true" ]]; then
  rm -f "${TOKEN_FILE}" || true
  echo "No auth-required post-deploy test suites enabled; skipping bearer token minting."
  exit 0
fi

if [[ -z "${FUNCTIONAL_FIREBASE_API_KEY_SECRET}" || -z "${FUNCTIONAL_TEST_EMAIL_SECRET}" || -z "${FUNCTIONAL_TEST_PASSWORD_SECRET}" ]]; then
  echo "Missing required substitutions for bearer token minting."
  echo "Set _FUNCTIONAL_FIREBASE_API_KEY_SECRET, _FUNCTIONAL_TEST_EMAIL_SECRET, and _FUNCTIONAL_TEST_PASSWORD_SECRET."
  exit 1
fi

firebase_api_key="$(gcloud secrets versions access latest --secret="${FUNCTIONAL_FIREBASE_API_KEY_SECRET}" | tr -d '\r\n')"
test_email="$(gcloud secrets versions access latest --secret="${FUNCTIONAL_TEST_EMAIL_SECRET}" | tr -d '\r\n')"
test_password="$(gcloud secrets versions access latest --secret="${FUNCTIONAL_TEST_PASSWORD_SECRET}" | tr -d '\r\n')"

if [[ -z "${firebase_api_key}" || -z "${test_email}" || -z "${test_password}" ]]; then
  echo "One or more Secret Manager values for functional token minting are empty."
  exit 1
fi

auth_payload="$(TEST_EMAIL="${test_email}" TEST_PASSWORD="${test_password}" python3 - <<'PY'
import json
import os
print(json.dumps({
    "email": os.environ["TEST_EMAIL"],
    "password": os.environ["TEST_PASSWORD"],
    "returnSecureToken": True,
}))
PY
)"

auth_response="$(curl -sS \
  "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${firebase_api_key}" \
  -H "Content-Type: application/json" \
  -d "${auth_payload}")"

id_token="$(
  printf '%s' "${auth_response}" | python3 - <<'PY'
import json
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)

print(payload.get("idToken", ""))
PY
)"

if [[ -z "${id_token}" ]]; then
  echo "Failed to mint FUNCTIONAL_BEARER_TOKEN from Firebase Identity Toolkit."
  exit 1
fi

umask 077
printf '%s' "${id_token}" > "${TOKEN_FILE}"
echo "Minted functional bearer token for post-deploy API tests."
