# API Contract (MVP)

Conventions:
- All authenticated endpoints require Firebase JWT (Authorization: Bearer <token>)
- Tenant is derived from JWT and enforced by server-side tenant isolation
- Approval link endpoints are token-protected and do not require JWT

Base URL (per env):
https://neilsolar-<env>-api.run.app

---

## Health
GET /health
Response:
- 200 OK { "status": "ok" }

---

## Customers
POST /customers
Body:
{
  "name": "ABC School Group",
  "address": "Lucknow",
  "status": "ACTIVE"
}

GET /customers
GET /customers/{customer_id}
PUT /customers/{customer_id}
DELETE /customers/{customer_id}

---

## Sites
POST /sites
Body:
{
  "customer_id": "<uuid>",
  "site_name": "LDA Colony Rooftop",
  "address": "Lucknow",
  "capacity_kw": 150,
  "status": "ACTIVE",
  "site_supervisor_name": "Mr. Sharma",
  "site_supervisor_phone": "+91XXXXXXXXXX"
}

GET /sites
GET /sites/{site_id}
PUT /sites/{site_id}
DELETE /sites/{site_id}

---

## Site Inverters (dynamic)
POST /sites/{site_id}/inverters
Body:
{
  "inverter_label": "INV-1",
  "inverter_capacity_kw": 25,
  "inverter_make": "SMA",
  "inverter_model": "XYZ",
  "serial_no": "SN123",
  "status": "ACTIVE"
}

GET /sites/{site_id}/inverters
PUT /inverters/{inverter_id}
DELETE /inverters/{inverter_id}

---

## WorkOrders (AMC Visits)

POST /workorders
Body:
{
  "site_id": "<uuid>",
  "assigned_tech_user_id": "<uuid>",
  "scheduled_at": "2026-03-10T10:00:00+05:30"
}

GET /workorders
Query:
- assigned_to=me (tech only)
- site_id=...
- status=...

GET /workorders/{workorder_id}

### Submit WorkOrder (tech)
POST /workorders/{workorder_id}/submit
Body:
{
  "visit_status": "NEEDS_ATTENTION",
  "summary_notes": "Earthing needs tightening",
  "inverter_readings": [
    { "inverter_id": "<uuid>", "power_kw": 20.1, "day_kwh": 85.2, "total_kwh": 12345.6 }
  ],
  "net_meter": { "net_kwh": 123.4, "imp_kwh": 567.8, "exp_kwh": 444.4 },
  "checklist_answers": {
    "solar_module_clean": { "value": "YES", "notes": "" },
    "inverter_status": { "value": "ON", "notes": "" },
    "earthing": { "value": "FAIL", "notes": "Loose connection at point A" }
  },
  "tech_signature": {
    "signer_name": "Tech Name",
    "signer_phone": "+91XXXXXXXXXX",
    "signature_object_path": "gcs://.../signatures/tech/..."
  },
  "media": [
    { "item_key": "net_meter", "object_path": "gcs://.../photos/...", "content_type": "image/jpeg", "size_bytes": 123456 }
  ]
}

Server rules:
- net_meter values are mandatory
- net meter photo is mandatory (at least one photo tagged item_key=net_meter)
- total photos per visit <= tenant.plan_limits.max_photos_per_visit (default 20)

Response:
- 200 OK { "status": "submitted" }

### Generate report (server/worker)
POST /workorders/{workorder_id}/generate-report
Response:
- 200 OK { "report_id": "<uuid>", "pdf_url": "<signed_url_or_path>" }

### Send approval (WhatsApp link)
POST /workorders/{workorder_id}/send-approval
Body:
{ "channel": "WHATSAPP" }

Response:
- 200 OK { "status": "sent", "approval_token_expires_at": "..." }

---

## Approval (Token endpoints – no JWT)

GET /approve/{token}
Response:
{
  "workorder_id": "<uuid>",
  "site_name": "...",
  "scheduled_at": "...",
  "visit_status": "NEEDS_ATTENTION",
  "report_pdf_url": "<signed_url>",
  "summary": { "pass_count": 10, "fail_count": 2 },
  "sign_required": true
}

POST /approve/{token}/sign
Body:
{
  "signer_name": "Customer Supervisor",
  "signer_phone": "+91XXXXXXXXXX",
  "signature_object_path": "gcs://.../signatures/customer/..."
}

Response:
- 200 OK { "status": "signed", "final_report_pdf_url": "<signed_url>" }

Server behavior:
- Marks workorder as CUSTOMER_SIGNED
- Regenerates final PDF (report.is_final=true)
- Writes audit log event

---

## Reports
GET /reports/{report_id}
Response:
{
  "report_id": "<uuid>",
  "workorder_id": "<uuid>",
  "pdf_url": "<signed_url>",
  "is_final": true,
  "generated_at": "..."
}

GET /logos/tenant

POST /logos/tenant

GET /logos/customers/{customer_id}

POST /logos/customers/{customer_id}