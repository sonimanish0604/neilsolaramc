# Runbook (Operations)

## First checks
- Cloud Run service health: /health
- Cloud Run logs: errors, timeouts
- Cloud SQL connectivity: connection errors, max connections
- GCS permissions: denied/forbidden errors

## Incident: API is down
1) Check Cloud Run service status and recent revisions
2) Review logs for startup failures
3) Roll back to previous revision (Cloud Run UI)
4) Confirm DB is reachable

## Incident: Report generation fails
1) Check worker job logs (HTML->PDF pipeline)
2) Confirm GCS write permissions for reports bucket
3) Confirm templates/assets exist
4) Retry generate-report endpoint

## Incident: WhatsApp sending fails
1) Check provider credentials secret
2) Check provider API responses (rate limit, template errors)
3) Retry job (manual rerun) for workorder

## Incident: Approval link issues
1) Confirm token not expired
2) Confirm token maps to correct workorder
3) Check signature upload path and permissions

## Backups
- Cloud SQL automated backups enabled (daily)
- PITR enabled when cost allows
- GCS objects are retained via lifecycle rules + app retention job

## Retention cleanup
Nightly worker job:
- Find reports/media older than tenant retention window
- Delete from GCS
- Mark records as deleted (or remove row) per policy
- Write audit log entries

## Migration (single project → multi project later)
Prereqs:
- One terraform state per env already in place

Steps (per env):
1) Create new GCP project
2) Apply Terraform with new project_id
3) Migrate Postgres (pg_dump/pg_restore or DMS)
4) Transfer GCS buckets (Storage Transfer Service or gsutil rsync)
5) Update secrets/IAM bindings
6) Deploy Cloud Run
7) Switch traffic / update URLs