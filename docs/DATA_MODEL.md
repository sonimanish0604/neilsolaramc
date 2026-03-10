
---

## `/docs/DATA_MODEL.md`

```markdown
# Data Model (Postgres) – MVP

All tables include:
- id (uuid)
- tenant_id (uuid)
- created_at, updated_at (timestamps)
- tenants.logo_object_path (nullable)

## Control Plane

### tenants
- id
- name
- plan_code (e.g., TRIAL, BASIC, PRO, ENTERPRISE)
- plan_limits (jsonb)
  - max_customers
  - max_sites
  - max_users
  - max_photos_per_visit (default 20)
  - pdf_retention_days (e.g., 90/365/1825)
  - media_retention_days (optional; usually same as pdf)
- status (ACTIVE/SUSPENDED)

### users
- id
- tenant_id
- firebase_uid (unique)
- name
- email (nullable)
- phone (nullable)
- status (ACTIVE/DISABLED)

### user_roles
- id
- tenant_id
- user_id
- role (OWNER | SUPERVISOR | TECH | CUSTOMER)

### invitations (optional for pilot; can be manual user creation)
- id
- tenant_id
- invited_email_or_phone
- role
- token
- expires_at
- status (PENDING/ACCEPTED/EXPIRED)

### audit_logs (append-only)
- id
- tenant_id
- actor_user_id (nullable for system)
- action (string)
- entity_type (string)
- entity_id (uuid, nullable)
- metadata (jsonb)
- created_at

---

## Application Plane

### customers
- id
- tenant_id
- name
- address (text)
- status (ACTIVE/INACTIVE)
- customers.logo_object_path (nullable)

### sites (AMC sites)
- id
- tenant_id
- customer_id
- site_name
- address (text)
- capacity_kw (numeric, nullable)
- status (ACTIVE/INACTIVE)
- site_supervisor_name
- site_supervisor_email
- site_supervisor_phone

### site_inverters (master data per site; dynamic count)
- id
- tenant_id
- site_id
- inverter_label (e.g., INV-1, SMA-25KW-01)
- inverter_capacity_kw (numeric, nullable)
- inverter_make (nullable)
- inverter_model (nullable)
- serial_no (nullable)
- status (ACTIVE/INACTIVE)

### checklist_templates
- id
- tenant_id (nullable if global)
- version (int)
- title
- is_active (bool)

### checklist_items
- id
- template_id
- section (e.g., "Solar Module", "Inverter", "Net Meter", "Safety")
- item_key (stable key, e.g., "solar_module_clean")
- item_text
- input_type (enum)
  - YES_NO
  - ON_OFF
  - AC_DC
  - NUMBER
  - TEXT
  - PASS_FAIL
- required (bool)
- is_photo_required (bool)
- max_photos_per_item (int, nullable)

### work_orders (AMC visit instances)
- id
- tenant_id
- site_id
- assigned_tech_user_id
- scheduled_at (timestamp)
- status (SCHEDULED/IN_PROGRESS/SUBMITTED/CUSTOMER_SIGNED/CLOSED)
- visit_status (SATISFACTORY/NEEDS_ATTENTION/CRITICAL)
- summary_notes (text, nullable)

### inverter_readings (per work order, per inverter)
- id
- tenant_id
- workorder_id
- inverter_id
- power_kw (numeric, nullable)   # P
- day_kwh (numeric, nullable)    # D
- total_kwh (numeric, nullable)  # T

### net_meter_readings (per work order)
- id
- tenant_id
- workorder_id
- net_kwh (numeric)  # mandatory
- imp_kwh (numeric)  # mandatory
- exp_kwh (numeric)  # mandatory

### checklist_responses
- id
- tenant_id
- workorder_id
- template_version (int)
- answers_json (jsonb)
  - map of item_key -> { value, notes, pass_fail(optional), ... }

### media (photos)
- id
- tenant_id
- workorder_id
- item_key (nullable; associate photo to checklist item)
- media_type (PHOTO)
- gcs_object_path
- content_type
- size_bytes
- created_by_user_id
- created_at

### signatures
- id
- tenant_id
- workorder_id
- signer_role (TECH | CUSTOMER_SUPERVISOR)
- signer_name
- signer_phone
- signature_gcs_object_path
- signed_at
- ip_address (nullable)
- user_agent (nullable)

### reports
- id
- tenant_id
- workorder_id
- report_version (int)
- pdf_gcs_object_path
- pdf_sha256
- pass_count (int)
- fail_count (int)
- generated_at
- is_final (bool)

### approval_events
- id
- tenant_id
- workorder_id
- channel (WHATSAPP | EMAIL | WEB)
- token
- expires_at
- status (QUEUED/SENT/OPENED/SIGNED/EXPIRED/REVOKED)
- created_at

### notification_events (outbox)
- id
- tenant_id
- event_type (e.g., `work_order.submitted_for_approval`)
- entity_type (e.g., `work_order`)
- entity_id
- payload_json
- status (PENDING/PROCESSING/PROCESSED/FAILED)
- attempt_count
- next_attempt_at
- processed_at
- last_error
- created_at

### tenant_notification_settings
- id
- tenant_id
- event_type
- enabled
- channels_json (e.g., `["EMAIL","WHATSAPP"]`)
- recipient_roles_json
- template_key
- created_at

### notification_templates
- id
- tenant_id
- template_key
- channel
- subject (nullable)
- body
- is_active
- created_at

### notification_logs
- id
- tenant_id
- event_id
- channel
- recipient
- status
- provider
- provider_message_id
- error_message
- sent_at
- created_at

### notification_delivery_jobs
- id
- tenant_id
- notification_event_id
- channel
- recipient
- subject (nullable)
- body
- status (PENDING/PROCESSING/SENT/FAILED/SKIPPED)
- attempt_count
- next_attempt_at
- processed_at
- last_error
- created_at
