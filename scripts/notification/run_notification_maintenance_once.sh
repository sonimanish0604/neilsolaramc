#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.local}"
MODE="${1:-}"

if [[ -z "${MODE}" ]]; then
  echo "Usage: $0 <archive|purge>"
  exit 1
fi

case "${MODE}" in
  archive) SERVICE="notification-maintenance-archive" ;;
  purge) SERVICE="notification-maintenance-purge" ;;
  *)
    echo "Unsupported mode: ${MODE}"
    exit 1
    ;;
esac

docker compose --env-file "${ENV_FILE}" --profile maintenance run --rm \
  -e NOTIFICATION_MAINTENANCE_RUN_ONCE=true \
  "${SERVICE}"
