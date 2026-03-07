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

echo "[integration] Happy path: create local auth user (AUTH_DISABLED=true identity)"
local_user_resp="$(curl -sS -X POST "${API_URL}/admin/users" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d "{\"tenant_id\":\"${tenant_id}\",\"firebase_uid\":\"local-dev-user\",\"name\":\"Local Dev Owner\",\"email\":\"owner@example.com\",\"status\":\"ACTIVE\"}")"
local_user_id="$(echo "${local_user_resp}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

echo "[integration] Happy path: assign OWNER role to local auth user"
local_role_code="$(curl -s -o /tmp/local_role.out -w "%{http_code}" -X POST "${API_URL}/admin/users/${local_user_id}/roles" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_KEY}" \
  -d '{"role":"OWNER"}')"
[[ "${local_role_code}" == "200" ]] || { echo "Expected 200 local role assign, got ${local_role_code}"; cat /tmp/local_role.out; exit 1; }

echo "[integration] Happy path: create customer"
customer_code="$(curl -s -o /tmp/customer.out -w "%{http_code}" -X POST "${API_URL}/customers" \
  -H "Content-Type: application/json" \
  -d '{"name":"CI Customer","address":"Mumbai","status":"ACTIVE"}')"
[[ "${customer_code}" == "200" ]] || { echo "Expected 200 customer create, got ${customer_code}"; cat /tmp/customer.out; exit 1; }
customer_id="$(python3 -c 'import json;print(json.load(open("/tmp/customer.out"))["id"])')"

echo "[integration] Rainy path: duplicate customer name -> 409"
dup_customer_code="$(curl -s -o /tmp/customer_dup.out -w "%{http_code}" -X POST "${API_URL}/customers" \
  -H "Content-Type: application/json" \
  -d '{"name":"CI Customer","address":"Mumbai","status":"ACTIVE"}')"
[[ "${dup_customer_code}" == "409" ]] || { echo "Expected 409 duplicate customer, got ${dup_customer_code}"; cat /tmp/customer_dup.out; exit 1; }

echo "[integration] Happy path: list customers"
customers_list_code="$(curl -s -o /tmp/customers_list.out -w "%{http_code}" -X GET "${API_URL}/customers")"
[[ "${customers_list_code}" == "200" ]] || { echo "Expected 200 customers list, got ${customers_list_code}"; cat /tmp/customers_list.out; exit 1; }

echo "[integration] Happy path: create site"
site_code="$(curl -s -o /tmp/site.out -w "%{http_code}" -X POST "${API_URL}/sites" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"${customer_id}\",\"site_name\":\"CI Site 1\",\"address\":\"Andheri\",\"capacity_kw\":10.5,\"status\":\"ACTIVE\",\"site_supervisor_name\":\"Supervisor\",\"site_supervisor_phone\":\"9999999999\"}")"
[[ "${site_code}" == "200" ]] || { echo "Expected 200 site create, got ${site_code}"; cat /tmp/site.out; exit 1; }
site_id="$(python3 -c 'import json;print(json.load(open("/tmp/site.out"))["id"])')"

echo "[integration] Rainy path: duplicate site name per customer -> 409"
dup_site_code="$(curl -s -o /tmp/site_dup.out -w "%{http_code}" -X POST "${API_URL}/sites" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"${customer_id}\",\"site_name\":\"CI Site 1\",\"address\":\"Andheri\",\"status\":\"ACTIVE\"}")"
[[ "${dup_site_code}" == "409" ]] || { echo "Expected 409 duplicate site, got ${dup_site_code}"; cat /tmp/site_dup.out; exit 1; }

echo "[integration] Happy path: list sites by customer filter"
sites_list_code="$(curl -s -o /tmp/sites_list.out -w "%{http_code}" -X GET "${API_URL}/sites?customer_id=${customer_id}")"
[[ "${sites_list_code}" == "200" ]] || { echo "Expected 200 sites list, got ${sites_list_code}"; cat /tmp/sites_list.out; exit 1; }

echo "[integration] Happy path: update customer"
upd_customer_code="$(curl -s -o /tmp/customer_upd.out -w "%{http_code}" -X PATCH "${API_URL}/customers/${customer_id}" \
  -H "Content-Type: application/json" \
  -d '{"address":"Pune","status":"INACTIVE"}')"
[[ "${upd_customer_code}" == "200" ]] || { echo "Expected 200 customer update, got ${upd_customer_code}"; cat /tmp/customer_upd.out; exit 1; }

echo "[integration] Happy path: update site"
upd_site_code="$(curl -s -o /tmp/site_upd.out -w "%{http_code}" -X PATCH "${API_URL}/sites/${site_id}" \
  -H "Content-Type: application/json" \
  -d '{"capacity_kw":12.0,"status":"INACTIVE"}')"
[[ "${upd_site_code}" == "200" ]] || { echo "Expected 200 site update, got ${upd_site_code}"; cat /tmp/site_upd.out; exit 1; }

echo "[integration] Rainy path: update unknown site -> 404"
missing_site_code="$(curl -s -o /tmp/site_missing.out -w "%{http_code}" -X PATCH "${API_URL}/sites/00000000-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{"status":"ACTIVE"}')"
[[ "${missing_site_code}" == "404" ]] || { echo "Expected 404 missing site, got ${missing_site_code}"; cat /tmp/site_missing.out; exit 1; }

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
