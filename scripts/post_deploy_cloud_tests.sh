#!/usr/bin/env bash
set -euo pipefail

SERVICE_URL="${SERVICE_URL:?SERVICE_URL is required}"
REPORT_DIR="${REPORT_DIR:-/workspace/reports}"
REPORT_BRANCH="${REPORT_BRANCH:-manual}"
ADMIN_KEY="${POST_DEPLOY_ADMIN_KEY:-dev-bootstrap-key}"
RUN_STATEFUL_TESTS="${RUN_STATEFUL_POST_DEPLOY_TESTS:-false}"

mkdir -p "${REPORT_DIR}"

JUNIT_FILE="${REPORT_DIR}/post_deploy_junit.xml"
SUMMARY_FILE="${REPORT_DIR}/post_deploy_summary.md"
EXIT_FILE="${REPORT_DIR}/post_deploy_exit_code.txt"

declare -a TEST_NAMES=()
declare -a TEST_EXPECTED=()
declare -a TEST_ACTUAL=()
declare -a TEST_STATUS=()

escape_xml() {
  echo "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
}

json_field() {
  local key="$1"
  local file="$2"
  sed -n "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" "${file}" | head -n1
}

run_test() {
  local name="$1"
  local expected="$2"
  local code="$3"

  TEST_NAMES+=("${name}")
  TEST_EXPECTED+=("${expected}")
  TEST_ACTUAL+=("${code}")
  if [[ "|${expected}|" == *"|${code}|"* ]]; then
    TEST_STATUS+=("PASS")
  else
    TEST_STATUS+=("FAIL")
  fi
}

http_code() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local out_file="$4"
  local admin="${5:-false}"

  local args=(-sS -o "${out_file}" -w "%{http_code}" -X "${method}" "${url}" -H "Content-Type: application/json")
  if [[ "${admin}" == "true" ]]; then
    args+=(-H "X-Admin-Key: ${ADMIN_KEY}")
  fi
  if [[ -n "${body}" ]]; then
    args+=(-d "${body}")
  fi
  curl "${args[@]}" || true
}

# 1) Always validate basic service availability.
HEALTH_CODE="$(http_code GET "${SERVICE_URL}/health" "" "${REPORT_DIR}/health.out")"
run_test "health endpoint" "200|401|403" "${HEALTH_CODE}"

READY_CODE="$(http_code GET "${SERVICE_URL}/ready" "" "${REPORT_DIR}/ready.out")"
run_test "ready endpoint" "200|401|403" "${READY_CODE}"

NOTFOUND_CODE="$(http_code GET "${SERVICE_URL}/__nonexistent__" "" "${REPORT_DIR}/notfound.out")"
run_test "non-existent endpoint returns 404" "404|401|403" "${NOTFOUND_CODE}"

# 2) Optional mutation checks for business APIs.
if [[ "${RUN_STATEFUL_TESTS}" == "true" ]]; then
  TENANT_NAME="ci-tenant-${REPORT_BRANCH}-${BUILD_ID:-manual}-$(date +%s)"
  TENANT_PAYLOAD="{\"name\":\"${TENANT_NAME}\",\"plan_code\":\"TRIAL\",\"status\":\"ACTIVE\"}"
  TENANT_CODE="$(http_code POST "${SERVICE_URL}/admin/tenants" "${TENANT_PAYLOAD}" "${REPORT_DIR}/tenant.out" "true")"
  run_test "admin create tenant (happy path)" "200" "${TENANT_CODE}"

  TENANT_ID="$(json_field id "${REPORT_DIR}/tenant.out")"
  if [[ -z "${TENANT_ID}" ]]; then
    TENANT_ID="00000000-0000-0000-0000-000000000000"
  fi

  TENANT_DUP_CODE="$(http_code POST "${SERVICE_URL}/admin/tenants" "${TENANT_PAYLOAD}" "${REPORT_DIR}/tenant_duplicate.out" "true")"
  run_test "admin create tenant duplicate (rainy path)" "409" "${TENANT_DUP_CODE}"

  TENANT_NO_KEY_CODE="$(http_code POST "${SERVICE_URL}/admin/tenants" "${TENANT_PAYLOAD}" "${REPORT_DIR}/tenant_missing_key.out" "false")"
  run_test "admin create tenant without admin key (rainy path)" "401|403" "${TENANT_NO_KEY_CODE}"

  FIREBASE_UID="ci-firebase-${REPORT_BRANCH}-${BUILD_ID:-manual}-$(date +%s)"
  USER_PAYLOAD="{\"tenant_id\":\"${TENANT_ID}\",\"firebase_uid\":\"${FIREBASE_UID}\",\"name\":\"CI User\",\"email\":\"ci-user@example.com\",\"status\":\"ACTIVE\"}"
  USER_CODE="$(http_code POST "${SERVICE_URL}/admin/users" "${USER_PAYLOAD}" "${REPORT_DIR}/user.out" "true")"
  run_test "admin create user (happy path)" "200" "${USER_CODE}"

  USER_ID="$(json_field id "${REPORT_DIR}/user.out")"
  if [[ -z "${USER_ID}" ]]; then
    USER_ID="00000000-0000-0000-0000-000000000000"
  fi

  USER_DUP_CODE="$(http_code POST "${SERVICE_URL}/admin/users" "${USER_PAYLOAD}" "${REPORT_DIR}/user_duplicate.out" "true")"
  run_test "admin create user duplicate firebase_uid (rainy path)" "409" "${USER_DUP_CODE}"

  USER_NO_KEY_CODE="$(http_code POST "${SERVICE_URL}/admin/users" "${USER_PAYLOAD}" "${REPORT_DIR}/user_missing_key.out" "false")"
  run_test "admin create user without admin key (rainy path)" "401|403" "${USER_NO_KEY_CODE}"

  ROLE_PAYLOAD='{"role":"SUPERVISOR"}'
  ROLE_CODE="$(http_code POST "${SERVICE_URL}/admin/users/${USER_ID}/roles" "${ROLE_PAYLOAD}" "${REPORT_DIR}/role.out" "true")"
  run_test "admin assign role (happy path)" "200" "${ROLE_CODE}"

  ROLE_DUP_CODE="$(http_code POST "${SERVICE_URL}/admin/users/${USER_ID}/roles" "${ROLE_PAYLOAD}" "${REPORT_DIR}/role_duplicate.out" "true")"
  run_test "admin assign duplicate role (rainy path)" "409" "${ROLE_DUP_CODE}"

  ROLE_INVALID_PAYLOAD='{"role":"INVALID_ROLE"}'
  ROLE_INVALID_CODE="$(http_code POST "${SERVICE_URL}/admin/users/${USER_ID}/roles" "${ROLE_INVALID_PAYLOAD}" "${REPORT_DIR}/role_invalid.out" "true")"
  run_test "admin assign invalid role (rainy path)" "400" "${ROLE_INVALID_CODE}"

  ROLE_USER_MISSING_CODE="$(http_code POST "${SERVICE_URL}/admin/users/00000000-0000-0000-0000-000000000001/roles" "${ROLE_PAYLOAD}" "${REPORT_DIR}/role_user_missing.out" "true")"
  run_test "admin assign role user not found (rainy path)" "404" "${ROLE_USER_MISSING_CODE}"

  ROLE_NO_KEY_CODE="$(http_code POST "${SERVICE_URL}/admin/users/${USER_ID}/roles" "${ROLE_PAYLOAD}" "${REPORT_DIR}/role_missing_key.out" "false")"
  run_test "admin assign role without admin key (rainy path)" "401|403" "${ROLE_NO_KEY_CODE}"
fi

# Build markdown summary.
{
  echo "# Post-Deploy API Test Summary"
  echo
  echo "- Service URL: \`${SERVICE_URL}\`"
  echo "- Branch: \`${REPORT_BRANCH}\`"
  echo "- Build ID: \`${BUILD_ID:-unknown}\`"
  echo
  echo "| Test | Expected | Actual | Status |"
  echo "|---|---:|---:|---|"
} > "${SUMMARY_FILE}"

FAILURES=0
TOTAL="${#TEST_NAMES[@]}"
for i in "${!TEST_NAMES[@]}"; do
  [[ "${TEST_STATUS[$i]}" == "FAIL" ]] && FAILURES=$((FAILURES + 1))
  echo "| ${TEST_NAMES[$i]} | ${TEST_EXPECTED[$i]} | ${TEST_ACTUAL[$i]} | ${TEST_STATUS[$i]} |" >> "${SUMMARY_FILE}"
done

{
  echo
  echo "- Total: ${TOTAL}"
  echo "- Failures: ${FAILURES}"
} >> "${SUMMARY_FILE}"

# Build simple JUnit report.
{
  echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
  echo "<testsuite name=\"post_deploy_api\" tests=\"${TOTAL}\" failures=\"${FAILURES}\">"
  for i in "${!TEST_NAMES[@]}"; do
    NAME_ESCAPED="$(escape_xml "${TEST_NAMES[$i]}")"
    echo "  <testcase classname=\"post_deploy\" name=\"${NAME_ESCAPED}\">"
    if [[ "${TEST_STATUS[$i]}" == "FAIL" ]]; then
      MSG_ESCAPED="$(escape_xml "expected ${TEST_EXPECTED[$i]} got ${TEST_ACTUAL[$i]}")"
      echo "    <failure message=\"${MSG_ESCAPED}\"/>"
    fi
    echo "  </testcase>"
  done
  echo "</testsuite>"
} > "${JUNIT_FILE}"

cat "${SUMMARY_FILE}"

if [[ "${FAILURES}" -gt 0 ]]; then
  echo "Post-deploy API tests failed: ${FAILURES}/${TOTAL}"
  echo "1" > "${EXIT_FILE}"
  exit 0
fi

echo "0" > "${EXIT_FILE}"
echo "Post-deploy API tests passed: ${TOTAL}/${TOTAL}"
