# Request Payload Examples (Current MVP)

All authenticated endpoints require:
- `Authorization: Bearer <Firebase JWT>`

---

## 1) Create Site (with supervisor contact)
`POST /sites`

```json
{
  "customer_id": "8d3e9c4f-5e7a-4c71-b2e4-1a2d3c4f5678",
  "site_name": "LDA Colony Rooftop",
  "address": "Lucknow",
  "capacity_kw": 150,
  "status": "ACTIVE",
  "site_supervisor_name": "Mr. Sharma",
  "site_supervisor_phone": "+919811112222",
  "site_supervisor_email": "supervisor@example.com"
}
```

Rule:
- at least one of `site_supervisor_phone` or `site_supervisor_email` is required.

---

## 2) Create WorkOrder
`POST /workorders`

```json
{
  "site_id": "8d3e9c4f-5e7a-4c71-b2e4-1a2d3c4f5678",
  "assigned_tech_user_id": "2a6c1b45-9876-4e11-8a33-abc123def456",
  "scheduled_at": "2026-03-10T10:00:00+05:30"
}
```

---

## 3) Submit WorkOrder
`POST /workorders/{workorder_id}/submit`

```json
{
  "visit_status": "NEEDS_ATTENTION",
  "summary_notes": "Earthing bolt loose near inverter 2",
  "inverter_readings": [
    {
      "inverter_id": "inv-uuid-1",
      "power_kw": 21.5,
      "day_kwh": 87.3,
      "total_kwh": 15432.7
    }
  ],
  "net_meter": {
    "net_kwh": 123.4,
    "imp_kwh": 567.8,
    "exp_kwh": 444.4
  },
  "checklist_answers": {
    "solar_module_clean": {"value": "YES", "notes": ""},
    "earthing_status": {"value": "FAIL", "notes": "Loose bolt"}
  },
  "media": [
    {
      "item_key": "net_meter_readings",
      "object_path": "neilsolar-dev-media/workorders/wo-12345/photos/net-meter-1.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 245678
    }
  ],
  "tech_signature": {
    "signer_name": "Ravi Kumar",
    "signer_phone": "+919876543210",
    "signature_object_path": "neilsolar-dev-media/workorders/wo-12345/signatures/tech.png"
  }
}
```

---

## 3A) Configure Site Inverter
`POST /sites/{site_id}/inverters`

```json
{
  "inverter_code": "INV-01",
  "display_name": "Inverter 01",
  "capacity_kw": 25,
  "manufacturer": "Sungrow",
  "model": "SG25CX",
  "serial_number": "SG25-001",
  "commissioned_on": "2018-04-20",
  "is_active": true
}
```

---

## 3B) Capture WorkOrder Inverter Reading
`POST /workorders/{workorder_id}/inverter-readings`

```json
{
  "inverter_id": "inv-uuid-1",
  "current_reading_kwh": 15432.7,
  "operational_status": "OPERATIONAL",
  "remarks": "Display clear",
  "photo_object_path": "neilsolar-dev-media/workorders/wo-12345/photos/inverter-01.jpg",
  "photo_content_type": "image/jpeg",
  "photo_size_bytes": 245678
}
```

When a reading is unavailable because the inverter is down:

```json
{
  "inverter_id": "inv-uuid-2",
  "current_reading_kwh": null,
  "operational_status": "OFFLINE",
  "remarks": "Display blank, breaker isolated",
  "photo_object_path": "neilsolar-dev-media/workorders/wo-12345/photos/inverter-02.jpg",
  "photo_content_type": "image/jpeg",
  "photo_size_bytes": 238001
}
```

---

## 4) Generate Report Async (idempotent)
`POST /workorders/{workorder_id}/generate-report-async`

```json
{
  "is_final": false,
  "idempotency_key": "phase1c-async-123"
}
```

Response shape:
```json
{
  "job_id": "<uuid>",
  "correlation_id": "<uuid>",
  "workorder_id": "<uuid>",
  "job_type": "DRAFT",
  "status": "QUEUED",
  "attempt_count": 0,
  "max_attempts": 3,
  "next_retry_at": null,
  "last_error": null,
  "generated_report_id": null,
  "report_pdf_url": null
}
```

---

## 5) Send Approval Link
`POST /workorders/{workorder_id}/send-approval`

Body: empty

Response shape:
```json
{
  "event_id": "<uuid>",
  "correlation_id": "<uuid>",
  "workorder_id": "<uuid>",
  "channel": "WHATSAPP",
  "recipient": "+919811112222",
  "status": "SENT",
  "token_expires_at": "2026-03-15T23:59:59+05:30",
  "approval_link": "http://localhost:8000/approve/<token>",
  "attempt_count": 1,
  "next_retry_at": null
}
```

---

## 6) Resend Approval Link
`POST /workorders/{workorder_id}/resend-approval`

```json
{
  "mode": "NEW_TOKEN"
}
```

`mode` options:
- `NEW_TOKEN` (supersedes prior token)
- `EXTEND` (extends current token TTL)

---

## 7) Run Approval Reminder Sweep
`POST /workorders/approval-reminders/run`

Body: empty

Response:
```json
{
  "scanned": 10,
  "reminders_sent": 2,
  "skipped": 8
}
```

---

## 8) Run/Retry Report Job
`POST /workorders/report-jobs/{job_id}/run`  
`POST /workorders/report-jobs/{job_id}/retry`

Body: empty

---

## 9) Customer Opens Approval Link
`GET /approve/{token}`

---

## 10) Customer Signs
`POST /approve/{token}/sign`

```json
{
  "signer_name": "Mr. Sharma",
  "signer_phone": "+919811112222",
  "signature_object_path": "neilsolar-dev-media/workorders/wo-12345/signatures/customer.png"
}
```

Response:
```json
{
  "status": "SIGNED",
  "final_report_pdf_url": "reports/<workorder_id>/report.pdf"
}
```
