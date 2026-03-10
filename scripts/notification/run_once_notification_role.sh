#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.local}"
ROLE="${1:-}"

if [[ -z "${ROLE}" ]]; then
  echo "Usage: $0 <ORCHESTRATOR|WORKER_EMAIL|WORKER_WHATSAPP|WORKER_SMS>"
  exit 1
fi

case "${ROLE}" in
  ORCHESTRATOR) SERVICE="notification-orchestrator" ;;
  WORKER_EMAIL) SERVICE="notification-worker-email" ;;
  WORKER_WHATSAPP) SERVICE="notification-worker-whatsapp" ;;
  WORKER_SMS) SERVICE="notification-worker-sms" ;;
  *)
    echo "Unsupported role: ${ROLE}"
    exit 1
    ;;
esac

docker compose --env-file "${ENV_FILE}" run --rm \
  -e "NOTIFICATION_ENGINE_ROLE=${ROLE}" \
  -e "NOTIFICATION_ENGINE_RUN_ONCE=true" \
  "${SERVICE}"
