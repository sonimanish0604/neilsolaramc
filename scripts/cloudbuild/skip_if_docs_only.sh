#!/usr/bin/env bash
set -euo pipefail

STEP_NAME="${1:-step}"
FLAGS_FILE="${FLAGS_FILE:-/workspace/.build_flags}"

if [[ -f "${FLAGS_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${FLAGS_FILE}"
fi

if [[ "${DOCS_ONLY:-false}" == "true" ]]; then
  echo "[${STEP_NAME}] Skipping step for docs-only change set."
  exit 0
fi
