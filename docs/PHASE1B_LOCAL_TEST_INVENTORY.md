# Phase 1B Local Test Inventory

This document describes exactly what `scripts/phase1b_local_api_tests.sh` runs when validating Phase 1B locally.

## Execution Flow

1. Starts Docker Compose stack from repo root using `.env.local` by default.
2. Waits for API health (`/health`) to return HTTP `200` before proceeding.
3. Runs targeted pytest suite inside the API container (unless `RUN_PHASE1B_PYTEST=false`).
4. Runs functional suite with Phase 1B scenarios:
   - `uc_1b_001_approval_token_flow`
   - `uc_1b_002_notification_email_smoke`
5. Produces summary + JUnit artifacts under `reports/phase1b-local/`.

## Pytest Target Files

These are the default targets in `PHASE1B_PYTEST_TARGETS`:

1. `tests/test_phase1b_services.py`
2. `tests/test_report_generation.py`
3. `tests/test_notification_engine_skeleton.py`
4. `tests/test_notification_events.py`
5. `tests/test_notification_runtime.py`
6. `tests/test_notification_maintenance.py`
7. `tests/test_email_adapter_routing.py`
8. `tests/test_mailgun_adapter.py`
9. `tests/test_secret_resolver.py`

## Pytest Case Inventory (32 Total)

### `backend/tests/test_phase1b_services.py` (7)

1. `test_generate_approval_token_entropy_batch`
2. `test_compute_expiry_iso_72h_policy`
3. `test_is_expired_iso_handles_utc`
4. `test_report_generation_changes_hash_for_customer_signed_variant`
5. `test_whatsapp_sender_skips_when_disabled`
6. `test_whatsapp_sender_success`
7. `test_whatsapp_sender_raises_on_provider_failure`

### `backend/tests/test_report_generation.py` (2)

1. `test_generate_report_pdf_local_roundtrip`
2. `test_generate_report_pdf_hash_changes_by_version_or_signature`

### `backend/tests/test_notification_engine_skeleton.py` (3)

1. `test_template_renderer_replaces_variables`
2. `test_recipient_resolver_email_uses_payload`
3. `test_recipient_resolver_whatsapp_payload`

### `backend/tests/test_notification_events.py` (3)

1. `test_send_approval_channel_supports_email_and_whatsapp`
2. `test_send_approval_channel_rejects_unknown`
3. `test_notification_event_payload_shape`

### `backend/tests/test_notification_runtime.py` (5)

1. `test_resolve_role_defaults_to_orchestrator`
2. `test_resolve_role_uses_worker_channel_backcompat`
3. `test_run_once_orchestrator`
4. `test_run_once_worker_email`
5. `test_read_bool_variants`

### `backend/tests/test_notification_maintenance.py` (4)

1. `test_to_utc_handles_naive_datetime`
2. `test_deactivated_tenant_purge_window_elapsed`
3. `test_active_tenant_not_purgeable`
4. `test_deactivated_but_recent_not_purgeable`

### `backend/tests/test_email_adapter_routing.py` (2)

1. `test_secondary_not_attempted_when_failover_disabled`
2. `test_secondary_attempted_when_failover_enabled_and_primary_failed`

### `backend/tests/test_mailgun_adapter.py` (3)

1. `test_send_mailgun_email_direct_success`
2. `test_send_mailgun_email_direct_provider_error`
3. `test_trysendemail_domain_selector_defaults_to_primary`

### `backend/tests/test_secret_resolver.py` (3)

1. `test_env_provider_returns_inline`
2. `test_vault_provider_fail_open_falls_back_to_inline`
3. `test_vault_provider_kv2_success`

## Functional Checks Run by Phase 1B Local Script

Functional suite always runs preflight checks first:

1. `preflight health endpoint`
   expected `200|401|403` for `GET /health`
2. `preflight ready endpoint`
   expected `200|401|403` for `GET /ready`
3. `preflight non-existent endpoint returns 404`
   expected `404|401|403` for `GET /__nonexistent__`

Then Phase 1B scenarios:

### `UC-1B-001` Approval Token Flow

1. `open approval link` -> expects `200` on `GET /approve/{token}`
2. `submit customer signature` -> expects `200` on `POST /approve/{token}/sign`
3. `reject token reuse` -> expects `409` on second `POST /approve/{token}/sign`

Skip condition: `FUNCTIONAL_APPROVAL_TOKEN` not provided.

### `UC-1B-002` Notification Email Smoke

1. `send notification test email` -> expects `200` on `POST /notifications/trysendemail`
2. `provider returned` -> expects one of `MAILGUN|TWILIO|SMTP`
3. `domain selector applied` -> expects selected domain id echo (`1` or `2`)

Skip condition: `FUNCTIONAL_PHASE1B_EMAIL_TO` not provided.

## Output Artifacts

Primary outputs written by the script:

1. `reports/phase1b-local/summary.md`
2. `reports/phase1b-local/pytest_output.txt`
3. `reports/phase1b-local/pytest_junit.xml`
4. `reports/phase1b-local/pytest_exit_code.txt`
5. `reports/phase1b-local/functional/summary.md`
6. `reports/phase1b-local/functional/junit.xml`
7. `reports/phase1b-local/functional/exit_code.txt`
