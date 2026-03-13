# Data Model (Postgres) – Current MVP

All tenant-scoped tables include:
- `id` (uuid)
- `tenant_id` (uuid)
- `created_at`, `updated_at` (timestamps)

## Control Plane

### tenants
- `name`, `plan_code`, `plan_limits`, `status`

### users
- `firebase_uid` (unique)
- `name`, `email`, `phone`, `status`

### user_roles
- `user_id`, `role` (`OWNER|SUPERVISOR|TECH|CUSTOMER`)

### audit_logs
- `actor`, `action`, `entity_type`, `entity_id`, `metadata_json`

## Application Plane

### customers
- `name`, `address`, `status`, `logo_object_path`

### sites
- `customer_id`, `site_name`, `address`, `capacity_kw`, `status`
- `site_supervisor_name`
- `site_supervisor_phone` (nullable)
- `site_supervisor_email` (nullable)
- `site_latitude` (nullable, optional in Phase 1E)
- `site_longitude` (nullable, optional in Phase 1E)
- rule: at least one contact channel (phone/email) must exist

### site_inverters
- `site_id`, `inverter_code`, `display_name`
- `capacity_kw` (nullable)
- `manufacturer`, `model`, `serial_number` (nullable)
- `commissioned_on` (nullable)
- `is_active`

### checklist_templates
- `title`, `version`, `is_active`

### checklist_items
- `template_id`, `section`, `item_key`, `item_text`, `input_type`
- `required`, `is_photo_required`, `max_photos_per_item`, `sort_order`, `options_json`

### work_orders
- `site_id`, `assigned_tech_user_id`, `scheduled_at`
- `status` (`SCHEDULED|IN_PROGRESS|SUBMITTED|CUSTOMER_SIGNED|CLOSED`)
- `visit_status`, `summary_notes`

### checklist_responses
- `workorder_id`, `template_version`, `answers_json`

### net_meter_readings
- `workorder_id`, `net_kwh`, `imp_kwh`, `exp_kwh`

### inverter_readings
- `workorder_id`, `inverter_id`, `power_kw`, `day_kwh`, `total_kwh`
- `current_reading_kwh`, `previous_reading_kwh`, `generation_delta_kwh`
- `is_baseline`, `is_anomaly`, `anomaly_reason`
- `device_latitude`, `device_longitude`, `device_accuracy_meters` (nullable)
- `photo_latitude`, `photo_longitude` (nullable, reserved for EXIF flow)
- `distance_to_site_meters`, `distance_photo_device_meters` (nullable)
- `geo_validation_status`, `geo_validation_reason` (nullable)
- `operational_status`, `remarks`, `captured_at`
- when site inventory is configured, `inverter_id` refers to `site_inverters.id`

### media
- `workorder_id`, `item_key`, `media_type`, `gcs_object_path`, `content_type`, `size_bytes`
- `inverter_reading_id` (nullable) for proof-photo linkage to captured inverter readings

### signatures
- `workorder_id`, `signer_role` (`TECH|CUSTOMER_SUPERVISOR`)
- `signer_name`, `signer_phone`, `signature_gcs_object_path`
- `signed_at`, `ip_address`, `user_agent`

### reports
- `workorder_id`, `report_version`
- `pdf_gcs_object_path`, `pdf_sha256`
- `pass_count`, `fail_count`, `generated_at`, `is_final`
- `generation_total_kwh` (nullable)
- `generation_snapshot_json` (nullable historical snapshot for report rendering)

### report_jobs
- `workorder_id`
- `job_type` (`DRAFT|FINAL`)
- `status` (`QUEUED|RUNNING|FAILED|DEAD|SUCCEEDED`)
- `idempotency_key`
- `correlation_id`
- `generated_report_id` (nullable)
- `attempt_count`, `max_attempts`, `next_retry_at`
- `simulate_failures_remaining` (non-prod test support)
- `started_at`, `completed_at`, `last_error`

### approval_events
- `workorder_id`, `channel`, `recipient`
- `token`, `expires_at`
- `status` (`QUEUED|SENT|OPENED|SIGNED|EXPIRED|SUPERSEDED|DELIVERY_FAILED|DELIVERY_PERMANENT_FAILED`)
- `correlation_id`
- `attempt_count`, `next_retry_at`, `last_error`
- `sent_at`, `opened_at`, `signed_at`
- `reminder_count`, `last_reminder_at`
- `superseded_by_event_id`

## Notes for Vertical Scalability
- Checklist data remains template-driven (`checklist_templates`, `checklist_items`).
- Responses are JSON-based (`answers_json`) keyed by stable `item_key`.
- This supports per-tenant and future multi-vertical template variation without schema rewrites.
