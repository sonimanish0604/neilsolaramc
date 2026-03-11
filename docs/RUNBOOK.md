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
1) Check report job state via API: `GET /workorders/report-jobs/{job_id}`
2) Check report job fields: `status`, `attempt_count`, `next_retry_at`, `last_error`
3) Check worker/service logs using `X-Correlation-ID`
4) Confirm GCS write permissions for reports bucket
5) Run/retry report job:
   - `POST /workorders/report-jobs/{job_id}/run`
   - `POST /workorders/report-jobs/{job_id}/retry`
6) If `DEAD`, perform operator review before manual retry.

## Incident: Approval delivery fails
1) Check latest approval event for workorder:
   - `status`, `attempt_count`, `next_retry_at`, `last_error`, `channel`, `recipient`
2) Classify failure:
   - retryable (`DELIVERY_FAILED`) should be retried by schedule/operator
   - permanent (`DELIVERY_PERMANENT_FAILED`) requires configuration/contact fix first
3) Trigger manual resend:
   - `POST /workorders/{workorder_id}/resend-approval` with `EXTEND` or `NEW_TOKEN`
4) For near-expiry reminders, run:
   - `POST /workorders/approval-reminders/run`

## Incident: Token supersession/expiry confusion
1) Identify active approval event and confirm token status.
2) If old token must be invalidated, resend with `NEW_TOKEN`.
3) Verify old token returns `410` and new token opens successfully.
4) Confirm `SUPERSEDED` status was written for previous token.

## Incident: Correlation/trace troubleshooting
1) Capture `X-Correlation-ID` from client response.
2) Use the same value to search API logs and event/job records.
3) Correlate path:
   - workorder action -> approval event/report job -> delivery/report result

## Incident: Legacy guidance (kept for transition)
Previous “retry generate-report endpoint” guidance is replaced by report-job APIs above.

## Incident: Channel provider send fails (WhatsApp/Email)
1) Check provider credentials secret
2) Check provider API responses (rate limit, template errors)
3) Retry/resend only after classifying retryable vs permanent

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

## Tracking Issues (Must Close Before Launch)

### SEC-001: Separate PROD DB Credentials From DEV
Status: Open
Priority: High

Current temporary state:
- `DATABASE_URL_PROD` and `DATABASE_ADMIN_URL_PROD` may reuse the same DB users/passwords as dev.

Required before MVP production launch:
1) Create prod-only DB users (app + admin).
2) Rotate `DATABASE_URL_PROD` and `DATABASE_ADMIN_URL_PROD` to prod-only credentials.
3) Confirm Cloud Run prod service deploys and starts with rotated secrets.
4) Revoke old shared credentials from prod service access path.

Launch gate:
- Do not launch production until SEC-001 is completed and verified.

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
