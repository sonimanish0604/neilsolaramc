# API Contract (Current MVP)

Conventions:
- Authenticated endpoints require Firebase JWT: `Authorization: Bearer <token>`
- Tenant context is derived from JWT and enforced server-side
- Approval-link endpoints (`/approve/*`) are token-protected and do not require JWT
- Correlation tracing:
  - Request may include `X-Correlation-ID` (optional)
  - API responses include `X-Correlation-ID`

Base URL (per env):
- `https://neilsolar-<env>-api.run.app`

---

## Health
- `GET /health`
- `GET /ready`

---

## Admin Bootstrap
- `POST /admin/tenants` (header: `X-Admin-Key`)
- `POST /admin/users` (header: `X-Admin-Key`)
- `POST /admin/users/{user_id}/roles` (header: `X-Admin-Key`)

---

## Customers
- `POST /customers`
- `GET /customers`
- `PATCH /customers/{customer_id}`

---

## Sites
- `POST /sites`
- `GET /sites`
- `PATCH /sites/{site_id}`
- `POST /sites/{site_id}/inverters`
- `GET /sites/{site_id}/inverters`
- `PATCH /sites/{site_id}/inverters/{inverter_id}`

Site contact requirements:
- At least one must be present:
  - `site_supervisor_phone`
  - `site_supervisor_email`

Site geo fields (Phase 1E Feature A):
- `site_latitude` (optional)
- `site_longitude` (optional)

---

## WorkOrders
- `POST /workorders`
- `GET /workorders` (supports `assigned_to=me`)
- `GET /workorders/{workorder_id}`
- `GET /workorders/{workorder_id}/inverters`
- `POST /workorders/{workorder_id}/inverter-readings`
- `GET /workorders/{workorder_id}/report-data`
- `POST /workorders/{workorder_id}/submit`
- `PATCH /workorders/{workorder_id}/status`

Lifecycle:
- `SCHEDULED -> IN_PROGRESS -> SUBMITTED -> CUSTOMER_SIGNED -> CLOSED`

Generation capture rules:
- Site inverter inventory drives the capture flow when configured.
- One active reading record is maintained per `workorder + inverter` by the API.
- Capture payload may include optional device location metadata:
  - `device_latitude`
  - `device_longitude`
  - `device_accuracy_meters`
- API computes and persists geo-validation fields on capture:
  - `geo_validation_status`
  - `geo_validation_reason`
  - `distance_to_site_meters`
- Prior generation comparison uses accepted/finalized prior work orders only.
- First accepted reading becomes the baseline and does not produce a generation delta.
- If current cumulative reading is lower than the latest accepted reading, the record is flagged as an anomaly and negative generation is not calculated.

---

## Approval Delivery APIs
- `POST /workorders/{workorder_id}/send-approval`
- `POST /workorders/{workorder_id}/resend-approval`
  - Body: `{ "mode": "NEW_TOKEN" | "EXTEND" }`
- `POST /workorders/approval-reminders/run`

Behavior highlights:
- Approval token TTL is `72h`
- `NEW_TOKEN` supersedes previous active token
- Provider delivery failures are classified:
  - retryable -> `DELIVERY_FAILED`
  - permanent -> `DELIVERY_PERMANENT_FAILED`

---

## Report Job APIs (Async + Retry)
- `POST /workorders/{workorder_id}/generate-report-async`
- `POST /workorders/{workorder_id}/generate-report` (enqueue + immediate run attempt)
- `GET /workorders/report-jobs/{job_id}`
- `POST /workorders/report-jobs/{job_id}/run`
- `POST /workorders/report-jobs/{job_id}/retry`

Report job states:
- `QUEUED`, `RUNNING`, `FAILED`, `DEAD`, `SUCCEEDED`

Idempotency:
- `idempotency_key` supported on report generation endpoints

---

## Approval Link APIs (No JWT)
- `GET /approve/{token}`
- `POST /approve/{token}/sign`

Token lifecycle statuses:
- `QUEUED`, `SENT`, `OPENED`, `SIGNED`, `EXPIRED`, `SUPERSEDED`

---

## Logo APIs
- `GET /logos/tenant`
- `POST /logos/tenant`
- `GET /logos/customers/{customer_id}`
- `POST /logos/customers/{customer_id}`

---

## Notes for MVP Focus
- Solar vertical is MVP focus.
- Architecture and data model remain extensible for additional verticals.
- Mailgun-backed email path is operational.
- SendGrid integration is intentionally parked for later phase.
