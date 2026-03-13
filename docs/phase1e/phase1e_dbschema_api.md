# Phase 1E - DB Schema and API Contract
## Geo Validation + OCR Validation

---

# Purpose

Define the backend database schema and API contracts for Phase 1E.

Phase 1E adds:

1. Geo-validation for inverter photo capture
2. OCR extraction for:
   - inverter serial number during asset registration
   - inverter cumulative reading during service visit

This phase assumes:

- Postgres is the authoritative backend database
- Cloud Storage stores photos
- Firestore, if used, is only a mobile draft/offline sync layer and not the final system of record

---

# Architecture Position

## Source of truth
Postgres is the final source of truth for:

- site inverter inventory
- confirmed inverter serial numbers
- OCR extraction results
- geo-validation results
- review flags
- finalized work-order inverter reading evidence

## File storage
Cloud Storage stores:

- inverter label photos
- inverter display photos

## Optional mobile sync
Firestore may be used for:

- mobile draft capture
- pending photo upload state
- temporary offline work-order state

Firestore should not be treated as the final evidence database.

---

# Database Schema

## 1. Table: site_inverters

Purpose:
Stores inverter master inventory for each site.

### Columns

- `id` UUID PRIMARY KEY
- `site_id` UUID NOT NULL
- `display_name` VARCHAR(100) NULL
- `inverter_code` VARCHAR(50) NULL
- `serial_number` VARCHAR(100) NOT NULL
- `manufacturer` VARCHAR(100) NULL
- `model` VARCHAR(100) NULL
- `capacity_kw` NUMERIC(10,2) NULL
- `label_photo_storage_path` TEXT NULL
- `label_photo_url` TEXT NULL
- `ocr_serial_number` VARCHAR(100) NULL
- `ocr_make` VARCHAR(100) NULL
- `ocr_model` VARCHAR(100) NULL
- `registration_ocr_confidence` NUMERIC(5,2) NULL
- `registration_ocr_status` VARCHAR(30) NULL
- `registration_ocr_raw_text` TEXT NULL
- `registration_review_required` BOOLEAN NOT NULL DEFAULT FALSE
- `is_active` BOOLEAN NOT NULL DEFAULT TRUE
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

### Constraints

- `UNIQUE (site_id, serial_number)`

### registration_ocr_status allowed values

- `success`
- `unreadable`
- `failed`
- `review_required`

---

## 2. Table: inverter_registration_ocr_audit

Purpose:
Stores OCR extraction attempts during inverter registration for auditability.

### Columns

- `id` UUID PRIMARY KEY
- `site_inverter_id` UUID NULL
- `site_id` UUID NOT NULL
- `photo_storage_path` TEXT NOT NULL
- `ocr_raw_text` TEXT NULL
- `ocr_serial_number` VARCHAR(100) NULL
- `ocr_make` VARCHAR(100) NULL
- `ocr_model` VARCHAR(100) NULL
- `ocr_confidence` NUMERIC(5,2) NULL
- `ocr_status` VARCHAR(30) NOT NULL
- `review_required` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMP NOT NULL

---

## 3. Table: inverter_readings

Purpose:
Stores inverter reading evidence captured during a work order.

### Columns

- `id` UUID PRIMARY KEY
- `workorder_id` UUID NOT NULL
- `site_id` UUID NOT NULL
- `inverter_id` UUID NOT NULL
- `technician_user_id` UUID NOT NULL
- `display_photo_storage_path` TEXT NULL
- `display_photo_url` TEXT NULL

### Geo fields
- `device_latitude` NUMERIC(10,7) NULL
- `device_longitude` NUMERIC(10,7) NULL
- `device_accuracy_meters` NUMERIC(10,2) NULL
- `photo_latitude` NUMERIC(10,7) NULL
- `photo_longitude` NUMERIC(10,7) NULL
- `distance_to_site_meters` NUMERIC(10,2) NULL
- `distance_photo_device_meters` NUMERIC(10,2) NULL
- `geo_validation_status` VARCHAR(40) NULL
- `geo_validation_reason` TEXT NULL

### OCR reading fields
- `ocr_reading_value` NUMERIC(14,2) NULL
- `ocr_raw_text` TEXT NULL
- `ocr_confidence_score` NUMERIC(5,2) NULL
- `ocr_processing_status` VARCHAR(30) NULL
- `ocr_review_required` BOOLEAN NOT NULL DEFAULT FALSE

### Final accepted reading fields
- `accepted_reading_value` NUMERIC(14,2) NULL
- `accepted_reading_source` VARCHAR(30) NULL
- `manual_corrected_value` NUMERIC(14,2) NULL
- `manual_correction_reason` TEXT NULL
- `review_status` VARCHAR(30) NULL
- `reviewed_by_user_id` UUID NULL
- `reviewed_at` TIMESTAMP NULL

### Existing generation fields
- `previous_reading_kwh` NUMERIC(14,2) NULL
- `generation_delta_kwh` NUMERIC(14,2) NULL
- `is_baseline` BOOLEAN NOT NULL DEFAULT FALSE
- `is_anomaly` BOOLEAN NOT NULL DEFAULT FALSE
- `anomaly_reason` TEXT NULL
- `operational_status` VARCHAR(30) NULL
- `remarks` TEXT NULL
- `captured_at` TIMESTAMP NOT NULL
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

### Constraints

- `UNIQUE (workorder_id, inverter_id)`

### geo_validation_status allowed values

- `verified`
- `outside_site_boundary`
- `missing_device_location`
- `missing_photo_location`
- `device_photo_mismatch`
- `geo_unverified`
- `low_accuracy`

### ocr_processing_status allowed values

- `success`
- `unreadable`
- `failed`
- `skipped`
- `review_required`

### accepted_reading_source allowed values

- `ocr`
- `manual`
- `supervisor_override`

### review_status allowed values

- `pending`
- `review_required`
- `approved`
- `rejected`
- `overridden`

---

## 4. Table: inverter_reading_ocr_audit

Purpose:
Stores OCR extraction attempts for inverter display photos.

### Columns

- `id` UUID PRIMARY KEY
- `reading_record_id` UUID NOT NULL
- `workorder_id` UUID NOT NULL
- `inverter_id` UUID NOT NULL
- `photo_storage_path` TEXT NOT NULL
- `ocr_raw_text` TEXT NULL
- `ocr_reading_value` NUMERIC(14,2) NULL
- `ocr_confidence_score` NUMERIC(5,2) NULL
- `ocr_status` VARCHAR(30) NOT NULL
- `review_required` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMP NOT NULL

---

## 5. Table: evidence_validation_config

Purpose:
Stores configurable validation thresholds.

### Columns

- `id` UUID PRIMARY KEY
- `tenant_id` UUID NULL
- `site_id` UUID NULL
- `max_site_distance_meters` NUMERIC(10,2) NOT NULL DEFAULT 200
- `max_photo_device_distance_meters` NUMERIC(10,2) NOT NULL DEFAULT 50
- `min_ocr_confidence` NUMERIC(5,2) NOT NULL DEFAULT 70
- `ocr_reading_tolerance_kwh` NUMERIC(10,2) NOT NULL DEFAULT 5
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

---

# API Contracts

## API 1 - Register inverter from label photo

### Endpoint
`POST /sites/{site_id}/inverters/register-from-photo`

### Purpose
Upload inverter label photo and extract probable serial number, make, and model.

### Request
Content-Type:
`multipart/form-data`

Fields:
- `photo` file (required)
- `display_name` string (optional)
- `inverter_code` string (optional)
- `capacity_kw` number (optional)

### Response
```json
{
  "site_id": "uuid",
  "label_photo_storage_path": "tenants/t1/sites/s1/inverters/tmp/photo1.jpg",
  "ocr_status": "success",
  "ocr_confidence": 91.5,
  "proposed_serial_number": "SJ2E5360N88118",
  "proposed_make": "Havells",
  "proposed_model": "envi GTI 50KT",
  "ocr_raw_text": "raw extracted text here",
  "review_required": false
}
```

## API 2 - Confirm inverter registration

### Endpoint
`POST /sites/{site_id}/inverters`

### Purpose

Create inverter asset using confirmed serial number and metadata.

### Request
```json
{
  "display_name": "Inverter 01",
  "inverter_code": "INV-01",
  "serial_number": "SJ2E5360N88118",
  "manufacturer": "Havells",
  "model": "envi GTI 50KT",
  "capacity_kw": 50,
  "label_photo_storage_path": "tenants/t1/sites/s1/inverters/tmp/photo1.jpg",
  "ocr_serial_number": "SJ2E5360N88118",
  "ocr_make": "Havells",
  "ocr_model": "envi GTI 50KT",
  "registration_ocr_confidence": 91.5,
  "registration_ocr_status": "success",
  "registration_ocr_raw_text": "raw extracted text here",
  "registration_review_required": false
}
```

### Response
```json
{
  "inverter_id": "uuid",
  "site_id": "uuid",
  "serial_number": "SJ2E5360N88118",
  "display_name": "Inverter 01",
  "manufacturer": "Havells",
  "model": "envi GTI 50KT",
  "is_active": true
}
```

## API 3 - Submit inverter reading from photo

### Endpoint
`POST /workorders/{workorder_id}/inverter-readings/from-photo`

### Purpose
Upload inverter display photo, capture device location, run geo-validation, run OCR, and persist reading evidence.

### Request
Content-Type:
`multipart/form-data`

Fields:
- `inverter_id` string required
- `photo` file required
- `device_latitude` number optional
- `device_longitude` number optional
- `device_accuracy_meters` number optional
- `captured_at` datetime required
- `operational_status` string optional
- `remarks` string optional

### Response
```json
{
  "reading_id": "uuid",
  "workorder_id": "uuid",
  "inverter_id": "uuid",
  "geo_validation": {
    "status": "verified",
    "distance_to_site_meters": 38.4,
    "distance_photo_device_meters": 6.1,
    "reason": null
  },
  "ocr_reading": {
    "status": "success",
    "value": 182345.7,
    "confidence": 88.2,
    "raw_text": "182345.7",
    "review_required": false
  },
  "accepted_reading": {
    "value": 182345.7,
    "source": "ocr"
  },
  "review_status": "pending"
}
```

Behavior:
- upload photo to Cloud Storage
- extract EXIF geotag if available
- compute geo distances and set geo validation status
- run OCR on display image
- if site coordinates are missing, set:
  - `geo_validation_status = geo_unverified`
  - `geo_validation_reason = missing_site_coordinates`
- if OCR confidence >= threshold and extraction succeeds, set:
  - `accepted_reading_value = ocr_reading_value`
  - `accepted_reading_source = ocr`
- if OCR fails / low confidence:
  - set `ocr_review_required = true`
  - keep `accepted_reading_value` null until manual/supervisor review
- create `inverter_reading_ocr_audit` row
- upsert `inverter_readings` row by `(workorder_id, inverter_id)`

## API 4 - Manual review / correction of OCR reading

### Endpoint
`POST /workorders/{workorder_id}/inverter-readings/{reading_id}/review`

### Purpose
Allow correction or override when OCR is unreadable, low-confidence, or mismatched.

### Request
```json
{
  "accepted_reading_value": 182345.7,
  "accepted_reading_source": "manual",
  "manual_corrected_value": 182345.7,
  "manual_correction_reason": "OCR unreadable due to glare",
  "review_status": "approved"
}
```

### Response
```json
{
  "workorder_id": "uuid",
  "site_id": "uuid",
  "inverters": [
    {
      "reading_id": "uuid",
      "inverter_id": "uuid",
      "serial_number": "SJ2E5360N88118",
      "display_name": "Inverter 01",
      "geo_validation_status": "verified",
      "distance_to_site_meters": 38.4,
      "ocr_processing_status": "success",
      "ocr_reading_value": 182345.7,
      "ocr_confidence_score": 88.2,
      "accepted_reading_value": 182345.7,
      "accepted_reading_source": "ocr",
      "review_status": "pending",
      "display_photo_url": "https://..."
    }
  ]
}
```

Finalization note

- No separate `finalize-readings` endpoint is introduced in Phase 1E.
- Existing lifecycle endpoints (`POST /workorders/{workorder_id}/submit` and approval closure flow) remain the finalization path.
- Generation logic continues to consume accepted values captured in `inverter_readings`.

Suggested DB Indexes
site_inverters

index on site_id

unique index on (site_id, serial_number)

inverter_readings

unique index on (workorder_id, inverter_id)

index on site_id

index on inverter_id

index on geo_validation_status

index on ocr_processing_status

index on review_status

inverter_registration_ocr_audit

index on site_id

index on site_inverter_id

inverter_reading_ocr_audit

index on reading_record_id

index on workorder_id

index on inverter_id

# Business Rules (Test-Ready)

| Rule ID | Rule | Expected behavior | Test assertion examples |
|---|---|---|---|
| BR-E1 | Serial number is unique within a site. | `site_inverters` enforces uniqueness on `(site_id, serial_number)`. | Create first inverter with serial `S1` -> success; create second inverter in same site with serial `S1` -> `409` (or DB uniqueness error mapped to conflict). |
| BR-E2 | Registration OCR is assistive, not authoritative. | `register-from-photo` returns proposed OCR fields; final create still requires confirmed `serial_number`. | OCR proposal response can differ from final confirmed payload; persisted `serial_number` equals confirmed request value. |
| BR-E3 | Reading OCR is first-pass extraction path. | `from-photo` flow attempts OCR and sets `ocr_processing_status`, `ocr_confidence_score`, `ocr_raw_text`. | Submit readable photo -> OCR status populated; unreadable photo -> `ocr_processing_status` in `unreadable/failed/review_required`. |
| BR-E4 | Manual correction is fallback path. | When OCR is low-confidence/unreadable, record is reviewable and may be corrected via review endpoint with `accepted_reading_source=manual` or `supervisor_override`. | Low-confidence OCR -> `ocr_review_required=true`; review call stores `accepted_reading_value`, `manual_corrected_value`, `review_status=approved`. |
| BR-E5 | Geo validation uses device-to-site distance as primary check. | System computes distance using `device_latitude/device_longitude` vs site coordinates and sets `geo_validation_status`. | Device within threshold -> `verified`; beyond threshold -> `outside_site_boundary`. |
| BR-E6 | Site coordinates are optional in Phase 1E. | If site coordinates are missing, geo result is not treated as verified; set `geo_validation_status=geo_unverified` with explicit reason. | Capture on site without `site_latitude/site_longitude` -> status `geo_unverified`, reason includes missing site coordinates. |
| BR-E7 | Photo EXIF location is secondary evidence. | If EXIF exists, compute secondary comparisons (photo->site and photo->device) and enrich geo reason/status as needed. | EXIF far from device but device near site -> status/ reason indicates mismatch (`device_photo_mismatch`) rather than silent pass. |
| BR-E8 | OCR and geo outcomes are auditable. | Each OCR attempt persists audit rows; primary reading row keeps geo/OCR/review state fields. | After capture, one row exists in `inverter_reading_ocr_audit`; `inverter_readings` row contains geo + OCR + review columns. |
| BR-E9 | Generation logic uses accepted reading value. | Downstream generation uses `accepted_reading_value` (not raw OCR text/value) for baseline/delta/anomaly computation. | OCR value `1000`, manual accepted value `1005` -> generation compares prior reading against `1005`. |

## Notes for Test Design
- Prefer one positive and one negative case for each rule ID.
- Keep rule ID tags (`BR-E1` ... `BR-E9`) in test names for traceability.
- Validate both API response and persisted DB state for evidence rules.
