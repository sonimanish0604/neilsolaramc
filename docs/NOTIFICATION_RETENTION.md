# Notification Retention and Purge (Canonical)

## 1. Objective

- Keep active queue tables small and fast.
- Preserve audit/history for sent and terminal notifications.
- Control growth with tenant-aware retention and purge.
- Use DB tables as source of truth (not flat files).

## 2. Storage Model

Use two tiers:

### Tier A: Active operational tables
- `notification_jobs_active`
- `notification_attempts_active`

### Tier B: History archive tables
- `notification_jobs_history`
- `notification_attempts_history`

Workers read only active tables. Audit/reporting reads history tables.

## 3. Lifecycle

1. Orchestrator inserts queued provider-agnostic jobs into `notification_jobs_active`.
2. Email worker writes provider attempts to `notification_attempts_active`.
3. Job reaches terminal status (`sent`, `failed`, `dead_lettered`, `cancelled`).
4. Archive maintenance moves terminal rows to history tables.
5. Active rows are deleted only after successful archive write.
6. Purge maintenance removes history beyond tenant policy.

## 4. Why No Immediate Delete

Do not delete sent rows immediately after delivery. Keep a short operational window in active tables to support:
- troubleshooting
- retry reconciliation
- provider/webhook lag handling

Suggested default active retention: `7` days.

## 5. Retention Policy and Tenant Status

Recommended policy table: `tenant_data_retention_policy`

Suggested columns:
- `tenant_id`
- `active_retention_days` (default `7`)
- `notification_history_retention_days` (default `365`)
- `dead_letter_retention_days` (default `365`)
- `purge_after_deactivation_days` (default `90`)
- `archive_enabled`
- `purge_enabled`
- `updated_at`

Purge logic must account for tenant lifecycle:
- `ACTIVE`
- `SUSPENDED`
- `DEACTIVATED`

## 6. Partitioning

Partition history tables monthly by `archived_at`, for example:
- `notification_jobs_history_y2026m03`
- `notification_attempts_history_y2026m03`

This enables low-cost time-range purges and smaller per-partition indexes.

## 7. Purge Safety Rules

- Never purge active tables directly.
- Purge only history rows/partitions older than policy.
- Keep separate retention for dead-letter history.
- Log each purge run with counts and timestamps.

## 8. Runtime Commands

One-shot archive:

```bash
bash scripts/notification/run_notification_maintenance_once.sh archive
```

One-shot purge:

```bash
bash scripts/notification/run_notification_maintenance_once.sh purge
```

Continuous services (docker compose profile):

```bash
docker compose --env-file .env.local --profile maintenance up -d \
  notification-maintenance-archive notification-maintenance-purge
```
