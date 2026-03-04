# Request Payload Examples – All Solar AMC SaaS (MVP)

All authenticated endpoints require:
Authorization: Bearer <Firebase JWT>

Tenant is derived from JWT and enforced server-side.

---

# 1️⃣ Create WorkOrder (Schedule AMC Visit)

POST /workorders

Request:
{
  "site_id": "8d3e9c4f-5e7a-4c71-b2e4-1a2d3c4f5678",
  "assigned_tech_user_id": "2a6c1b45-9876-4e11-8a33-abc123def456",
  "scheduled_at": "2026-03-10T10:00:00+05:30"
}

Response:
{
  "id": "wo-12345",
  "status": "SCHEDULED"
}

---

# 2️⃣ Get Assigned WorkOrders (Technician)

GET /workorders?assigned_to=me

Response:
[
  {
    "id": "wo-12345",
    "site_name": "LDA Colony Rooftop",
    "scheduled_at": "2026-03-10T10:00:00+05:30",
    "status": "SCHEDULED"
  }
]

---

# 3️⃣ Submit WorkOrder (Technician Completion)

POST /workorders/{workorder_id}/submit

Request:
{
  "visit_status": "NEEDS_ATTENTION",
  "summary_notes": "Earthing bolt loose near inverter 2",

  "inverter_readings": [
    {
      "inverter_id": "inv-uuid-1",
      "power_kw": 21.5,
      "day_kwh": 87.3,
      "total_kwh": 15432.7
    },
    {
      "inverter_id": "inv-uuid-2",
      "power_kw": 22.1,
      "day_kwh": 90.0,
      "total_kwh": 16002.3
    }
  ],

  "net_meter": {
    "net_kwh": 123.4,
    "imp_kwh": 567.8,
    "exp_kwh": 444.4
  },

  "checklist_answers": {
    "solar_module_clean": {
      "value": "YES",
      "notes": ""
    },
    "inverter_cabling": {
      "value": "AC",
      "notes": ""
    },
    "inverter_status": {
      "value": "ON",
      "notes": ""
    },
    "structure_condition": {
      "value": "PASS",
      "notes": ""
    },
    "earthing_status": {
      "value": "FAIL",
      "notes": "Loose bolt near grounding strip"
    },
    "lightning_arrester_status": {
      "value": "PASS",
      "notes": ""
    },
    "monitoring_system_status": {
      "value": "PASS",
      "notes": ""
    },
    "conduit_pipe_status": {
      "value": "PASS",
      "notes": ""
    },
    "acdb_ajb_status": {
      "value": "PASS",
      "notes": ""
    }
  },

  "media": [
    {
      "item_key": "net_meter_readings",
      "object_path": "allsolar-dev-media/workorders/wo-12345/photos/net-meter-1.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 245678
    },
    {
      "item_key": "earthing_status",
      "object_path": "allsolar-dev-media/workorders/wo-12345/photos/earthing-issue.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 187543
    }
  ],

  "tech_signature": {
    "signer_name": "Ravi Kumar",
    "signer_phone": "+919876543210",
    "signature_object_path": "allsolar-dev-media/workorders/wo-12345/signatures/tech.png"
  }
}

Server Validations:
- net_kwh, imp_kwh, exp_kwh are mandatory
- At least 1 photo where item_key == "net_meter_readings"
- Total photos <= tenant.plan_limits.max_photos_per_visit
- visit_status is required
- tech_signature required

Response:
{
  "status": "SUBMITTED",
  "message": "WorkOrder submitted successfully"
}

---

# 4️⃣ Generate Report (Async Trigger)

POST /workorders/{workorder_id}/generate-report

Response:
{
  "report_id": "report-uuid-123",
  "pdf_url": "https://storage.googleapis.com/allsolar-dev-reports/..."
}

---

# 5️⃣ Send Approval Link (WhatsApp)

POST /workorders/{workorder_id}/send-approval

Request:
{
  "channel": "WHATSAPP"
}

Response:
{
  "status": "SENT",
  "approval_token": "random-secure-token",
  "expires_at": "2026-03-15T23:59:59+05:30"
}

---

# 6️⃣ Customer Opens Approval Link

GET /approve/{token}

Response:
{
  "workorder_id": "wo-12345",
  "site_name": "LDA Colony Rooftop",
  "visit_status": "NEEDS_ATTENTION",
  "scheduled_at": "2026-03-10T10:00:00+05:30",
  "summary": {
    "pass_count": 8,
    "fail_count": 1
  },
  "report_pdf_url": "https://signed-url-to-pdf",
  "sign_required": true
}

---

# 7️⃣ Customer Signs

POST /approve/{token}/sign

Request:
{
  "signer_name": "Mr. Sharma",
  "signer_phone": "+919811112222",
  "signature_object_path": "allsolar-dev-media/workorders/wo-12345/signatures/customer.png"
}

Response:
{
  "status": "SIGNED",
  "final_report_pdf_url": "https://signed-url-to-final-pdf"
}

Server Actions:
- Validate token not expired
- Insert signature row (CUSTOMER_SUPERVISOR)
- Regenerate final PDF (is_final = true)
- Update workorder status → CUSTOMER_SIGNED
- Write audit_log entry