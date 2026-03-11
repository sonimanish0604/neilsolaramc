#!/usr/bin/env bash
set -euo pipefail

FLAGS_FILE="${FLAGS_FILE:-/workspace/.build_flags}"
CHANGED_FILE_LIST="${CHANGED_FILE_LIST:-/workspace/.changed_files.txt}"

OVERRIDE="${_DOCS_ONLY_OVERRIDE:-auto}"
FORCE_FULL="${_FORCE_FULL_PIPELINE:-false}"

mkdir -p "$(dirname "${FLAGS_FILE}")"

if [[ "${FORCE_FULL}" == "true" ]]; then
  echo "DOCS_ONLY=false" > "${FLAGS_FILE}"
  echo "REASON=force_full_pipeline" >> "${FLAGS_FILE}"
  echo "Forced full pipeline enabled."
  exit 0
fi

if [[ "${OVERRIDE}" == "true" || "${OVERRIDE}" == "false" ]]; then
  echo "DOCS_ONLY=${OVERRIDE}" > "${FLAGS_FILE}"
  echo "REASON=explicit_override" >> "${FLAGS_FILE}"
  echo "DOCS_ONLY override applied: ${OVERRIDE}"
  exit 0
fi

# Safe default: run full pipeline unless we can confidently classify docs-only.
DOCS_ONLY=false
REASON="unable_to_classify"

if [[ -d .git ]]; then
  if git rev-parse --verify HEAD >/dev/null 2>&1; then
    if git rev-parse --verify HEAD^ >/dev/null 2>&1; then
      git diff --name-only HEAD^ HEAD > "${CHANGED_FILE_LIST}" || true
    else
      # Initial commit fallback
      git show --pretty="" --name-only HEAD > "${CHANGED_FILE_LIST}" || true
    fi

    if [[ -s "${CHANGED_FILE_LIST}" ]]; then
      DOCS_ONLY=true
      REASON="git_diff"
      while IFS= read -r path; do
        [[ -z "${path}" ]] && continue
        case "${path}" in
          docs/*|README.md)
            ;;
          *)
            DOCS_ONLY=false
            REASON="non_docs_change_detected"
            break
            ;;
        esac
      done < "${CHANGED_FILE_LIST}"
    else
      DOCS_ONLY=false
      REASON="no_changed_files_detected"
    fi
  fi
fi

echo "DOCS_ONLY=${DOCS_ONLY}" > "${FLAGS_FILE}"
echo "REASON=${REASON}" >> "${FLAGS_FILE}"

echo "Build classification: DOCS_ONLY=${DOCS_ONLY} (${REASON})"
if [[ -f "${CHANGED_FILE_LIST}" ]]; then
  echo "Changed files:"
  cat "${CHANGED_FILE_LIST}"
fi
