#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE=".env.local.example"
API_URL="http://localhost:8080"
ADMIN_KEY="dev-bootstrap-key"

cleanup() {
  docker compose --env-file "${ENV_FILE}" down -v || true
}
trap cleanup EXIT

echo "[integration] Starting local stack with Docker Compose"
docker compose --env-file "${ENV_FILE}" up -d --build

echo "[integration] Waiting for API health"
for _ in $(seq 1 60); do
  code="$(curl -s -o /tmp/health.out -w "%{http_code}" "${API_URL}/health" || true)"
  if [[ "${code}" == "200" ]]; then
    break
  fi
  sleep 2
done

code="$(curl -s -o /tmp/health.out -w "%{http_code}" "${API_URL}/health" || true)"
if [[ "${code}" != "200" ]]; then
  echo "[integration] health check failed with HTTP ${code}"
  cat /tmp/health.out || true
  exit 1
fi

echo "[integration] Happy path: create tenant"
tenant_resp="$(curl -sS -X POST "${API_URL}/admin/tenants" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d '{"name":"CI Tenant","plan_code":"TRIAL","status":"ACTIVE"}')"
tenant_id="$(echo "${tenant_resp}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

echo "[integration] Happy path: create user"
user_resp="$(curl -sS -X POST "${API_URL}/admin/users" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d "{\"tenant_id\":\"${tenant_id}\",\"firebase_uid\":\"ci-user-1\",\"name\":\"CI Owner\",\"email\":\"ci-owner@example.com\",\"status\":\"ACTIVE\"}")"
user_id="$(echo "${user_resp}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

echo "[integration] Happy path: assign role"
role_code="$(curl -s -o /tmp/role.out -w "%{http_code}" -X POST "${API_URL}/admin/users/${user_id}/roles" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d '{"role":"OWNER"}')"
[[ "${role_code}" == "200" ]] || { echo "Expected 200 role assign, got ${role_code}"; cat /tmp/role.out; exit 1; }

echo "[integration] Rainy path: duplicate tenant -> 409"
dup_tenant_code="$(curl -s -o /tmp/dup_tenant.out -w "%{http_code}" -X POST "${API_URL}/admin/tenants" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d '{"name":"CI Tenant","plan_code":"TRIAL","status":"ACTIVE"}')"
[[ "${dup_tenant_code}" == "409" ]] || { echo "Expected 409 duplicate tenant, got ${dup_tenant_code}"; cat /tmp/dup_tenant.out; exit 1; }

echo "[integration] Rainy path: duplicate user firebase_uid -> 409"
dup_user_code="$(curl -s -o /tmp/dup_user.out -w "%{http_code}" -X POST "${API_URL}/admin/users" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d "{\"tenant_id\":\"${tenant_id}\",\"firebase_uid\":\"ci-user-1\",\"name\":\"Duplicate User\",\"status\":\"ACTIVE\"}")"
[[ "${dup_user_code}" == "409" ]] || { echo "Expected 409 duplicate user, got ${dup_user_code}"; cat /tmp/dup_user.out; exit 1; }

echo "[integration] Rainy path: invalid role -> 400"
bad_role_code="$(curl -s -o /tmp/bad_role.out -w "%{http_code}" -X POST "${API_URL}/admin/users/${user_id}/roles" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d '{"role":"INVALID_ROLE"}')"
[[ "${bad_role_code}" == "400" ]] || { echo "Expected 400 invalid role, got ${bad_role_code}"; cat /tmp/bad_role.out; exit 1; }

echo "[integration] Rainy path: missing admin key -> 401"
missing_key_code="$(curl -s -o /tmp/missing_key.out -w "%{http_code}" -X POST "${API_URL}/admin/tenants" \
  -H "Content-Type: application/json" \
  -d '{"name":"NoKeyTenant","plan_code":"TRIAL","status":"ACTIVE"}')"
[[ "${missing_key_code}" == "401" ]] || { echo "Expected 401 missing admin key, got ${missing_key_code}"; cat /tmp/missing_key.out; exit 1; }

echo "[integration] All compose integration checks passed"
