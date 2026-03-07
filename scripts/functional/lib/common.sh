#!/usr/bin/env bash
set -euo pipefail

declare -ga TEST_NAMES=()
declare -ga TEST_EXPECTED=()
declare -ga TEST_ACTUAL=()
declare -ga TEST_STATUS=()

escape_xml() {
  echo "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
}

json_field() {
  local key="$1"
  local file="$2"
  python3 - "$key" "$file" <<'PY'
import json, sys
key, path = sys.argv[1], sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(data.get(key, ""))
except Exception:
    print("")
PY
}

run_test() {
  local name="$1"
  local expected="$2"
  local actual="$3"
  TEST_NAMES+=("${name}")
  TEST_EXPECTED+=("${expected}")
  TEST_ACTUAL+=("${actual}")
  if [[ "|${expected}|" == *"|${actual}|"* ]]; then
    TEST_STATUS+=("PASS")
  else
    TEST_STATUS+=("FAIL")
  fi
}

run_skip() {
  local name="$1"
  local reason="$2"
  TEST_NAMES+=("${name}")
  TEST_EXPECTED+=("N/A")
  TEST_ACTUAL+=("${reason}")
  TEST_STATUS+=("SKIP")
}

http_code() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local out_file="$4"
  local admin="${5:-false}"
  local bearer="${6:-}"

  local args=(-sS -o "${out_file}" -w "%{http_code}" -X "${method}" "${url}" -H "Content-Type: application/json")
  if [[ "${admin}" == "true" ]]; then
    args+=(-H "X-Admin-Key: ${ADMIN_KEY}")
  fi
  if [[ -n "${bearer}" ]]; then
    args+=(-H "Authorization: Bearer ${bearer}")
  fi
  if [[ -n "${body}" ]]; then
    args+=(-d "${body}")
  fi
  curl "${args[@]}" || true
}

write_reports() {
  local suite_title="$1"
  local service_url="$2"
  local branch="$3"
  local build_id="$4"
  local summary_file="$5"
  local junit_file="$6"
  local exit_file="$7"

  {
    echo "# ${suite_title}"
    echo
    echo "- Service URL: \`${service_url}\`"
    echo "- Branch: \`${branch}\`"
    echo "- Build ID: \`${build_id}\`"
    echo "- Timestamp: \`$(date -u +"%Y-%m-%dT%H:%M:%SZ")\`"
    echo
    echo "| Test | Expected | Actual | Status |"
    echo "|---|---:|---:|---|"
  } > "${summary_file}"

  local failures=0
  local total="${#TEST_NAMES[@]}"
  local skips=0

  for i in "${!TEST_NAMES[@]}"; do
    [[ "${TEST_STATUS[$i]}" == "FAIL" ]] && failures=$((failures + 1))
    [[ "${TEST_STATUS[$i]}" == "SKIP" ]] && skips=$((skips + 1))
    echo "| ${TEST_NAMES[$i]} | ${TEST_EXPECTED[$i]} | ${TEST_ACTUAL[$i]} | ${TEST_STATUS[$i]} |" >> "${summary_file}"
  done

  {
    echo
    echo "- Total: ${total}"
    echo "- Failures: ${failures}"
    echo "- Skips: ${skips}"
  } >> "${summary_file}"

  {
    echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    echo "<testsuite name=\"functional_suite\" tests=\"${total}\" failures=\"${failures}\" skipped=\"${skips}\">"
    for i in "${!TEST_NAMES[@]}"; do
      local name_escaped
      name_escaped="$(escape_xml "${TEST_NAMES[$i]}")"
      echo "  <testcase classname=\"functional\" name=\"${name_escaped}\">"
      if [[ "${TEST_STATUS[$i]}" == "FAIL" ]]; then
        local msg_escaped
        msg_escaped="$(escape_xml "expected ${TEST_EXPECTED[$i]} got ${TEST_ACTUAL[$i]}")"
        echo "    <failure message=\"${msg_escaped}\"/>"
      fi
      if [[ "${TEST_STATUS[$i]}" == "SKIP" ]]; then
        local skip_escaped
        skip_escaped="$(escape_xml "${TEST_ACTUAL[$i]}")"
        echo "    <skipped message=\"${skip_escaped}\"/>"
      fi
      echo "  </testcase>"
    done
    echo "</testsuite>"
  } > "${junit_file}"

  echo "${summary_file}"
  if [[ "${failures}" -gt 0 ]]; then
    echo "1" > "${exit_file}"
  else
    echo "0" > "${exit_file}"
  fi
}

