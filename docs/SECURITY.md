# Security

## Authentication
- Firebase Auth for user identity
- FastAPI verifies Firebase JWT for all authenticated endpoints

## Authorization (RBAC)
Roles:
- OWNER
- SUPERVISOR
- TECH
- CUSTOMER

Role enforcement:
- Supervisor/Owner manage customers/sites/workorders
- Technician only sees assigned workorders
- Customer only sees their sites/reports

## Tenant Isolation
- Every table includes tenant_id
- Tenant is derived from JWT
- All queries are filtered by tenant_id in service layer

## Approval Link Security
- Approval link is tokenized: /approve/{token}
- Token is:
  - random, unguessable
  - time-bound (expires_at)
  - single-purpose (signing/approval)
- Signing events are written to audit_logs with:
  - timestamp
  - signer phone
  - IP and user-agent (best effort)

## Data Protection
- Media/PDF stored in GCS (no blobs in Postgres)
- Access via Signed URLs
- PDF hash (sha256) stored for tamper-evidence

## Audit Logging (SOC2-ready engineering)
- All mutations produce audit_logs events:
  - create/update/delete customers, sites, inverters, workorders
  - submit workorder
  - generate report
  - send approval link
  - customer signature captured
  - retention deletion actions

## Retention
Retention is plan-driven:
- PDFs/media deleted after tenant.plan_limits.pdf_retention_days
- Retention cleanup runs nightly in worker job