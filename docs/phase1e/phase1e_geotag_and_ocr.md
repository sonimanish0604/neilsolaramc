# Phase 1E - Geo Validation and OCR Validation

## Goal

Add backend/core support for:
1. geo-validation of inverter photo capture
2. OCR extraction for:
   - inverter serial number during site asset registration
   - inverter cumulative reading during service visit

This phase strengthens trust in field evidence and reduces manual entry.

---

## Scope

### In scope
- capture device GPS during photo capture
- store photo metadata
- validate technician location against site coordinates
- OCR serial number from inverter label photo
- OCR cumulative reading from inverter display photo
- store OCR result, confidence, status
- allow manual review/correction only when OCR fails or confidence is low

### Out of scope
- advanced AI fraud detection
- hard blocking every OCR failure
- replacing all manual fallback paths
- performance score and charts
- inverter asset-level geo-tagging and inverter-to-site proximity validation (deferred to Feature-4)

---

## Feature A - Geo Validation

### Purpose
Verify that inverter photos are captured near the actual site.

### Required data
- site_latitude (optional in Phase 1E; may become mandatory later)
- site_longitude (optional in Phase 1E; may become mandatory later)
- device_latitude
- device_longitude
- device_accuracy_meters
- photo_exif_latitude (optional)
- photo_exif_longitude (optional)

### Rule
Primary rule:

`distance(device_location, site_location) <= 200 meters`

### Additional rule
If photo EXIF location exists:

- compare photo location to site location
- compare photo location to device location

### Geo validation statuses
- verified
- outside_site_boundary
- missing_device_location
- missing_photo_location
- device_photo_mismatch
- geo_unverified

### Recommended behavior
- if outside threshold, flag for review
- do not silently mark as valid
- if site coordinates are missing, set `geo_validation_status=geo_unverified` with an explicit reason
- allow configurable business policy later for blocking finalization

---

## Feature B - OCR for Inverter Registration

### Purpose
When adding inverter assets to a site, extract serial number from inverter label photo.

### Input
- inverter label/nameplate photo

### Output fields
- ocr_serial_number
- ocr_make
- ocr_model
- ocr_confidence_score
- ocr_processing_status

### Processing status
- success
- unreadable
- failed
- review_required

### Rule
- serial number extracted from photo should be stored as proposed value
- user/admin can confirm or correct before final save
- confirmed serial number becomes unique inverter identifier in site inventory

### Site inverter uniqueness
Use confirmed serial number as unique business identifier for inverter.

Recommended DB constraint:
- unique(site_id, serial_number)

---

## Feature C - OCR for Inverter Reading

### Purpose
During visit, extract cumulative generation reading from inverter display photo.

### Input
- inverter display photo

### Output fields
- ocr_reading_value
- ocr_raw_text
- ocr_confidence_score
- ocr_processing_status
- ocr_review_required

### Processing status
- success
- unreadable
- failed
- review_required

### MVP behavior
- OCR reading is attempted automatically
- if confidence is acceptable, store extracted reading
- if OCR fails or confidence is low, mark review_required
- fallback/manual correction path may exist, but should be exception flow, not primary flow

---

## Data Model Changes

### site_inverters
Add fields:
- serial_number
- label_photo_url
- ocr_serial_number
- ocr_make
- ocr_model
- registration_ocr_confidence
- registration_ocr_status

### inverter_readings
Add fields:
- device_latitude
- device_longitude
- device_accuracy_meters
- photo_latitude
- photo_longitude
- distance_to_site_meters
- distance_photo_device_meters
- geo_validation_status
- geo_validation_reason
- ocr_reading_value
- ocr_raw_text
- ocr_confidence_score
- ocr_processing_status
- ocr_review_required

---

## APIs

### 1. Register inverter from label photo
`POST /sites/{site_id}/inverters/register-from-photo`

Request:
- label photo
- optional display name / inverter code

Response:
- proposed serial number
- proposed make/model
- OCR status
- confidence

### 2. Confirm inverter registration
`POST /sites/{site_id}/inverters`

Request:
- confirmed serial number
- display name
- make/model
- capacity
- label photo reference

### 3. Submit inverter visit photo
`POST /workorders/{workorder_id}/inverter-readings/from-photo`

Request:
- inverter_id or serial_number
- display photo
- device latitude/longitude/accuracy

Response:
- OCR reading result
- geo validation result
- review flags

---

## Backend Services

Create services:
- GeoValidationService
- InverterRegistrationOCRService
- InverterReadingOCRService
- EvidenceValidationService

### GeoValidationService
- calculate distance to site
- evaluate geo status

### InverterRegistrationOCRService
- extract serial number, make, model from label photo

### InverterReadingOCRService
- extract cumulative reading from display photo

### EvidenceValidationService
- combine OCR + geo results
- persist statuses and review flags

---

## Acceptance Criteria

1. System can extract serial number from inverter label photo.
2. Serial number can be confirmed and saved as unique inverter identifier.
3. System can attempt OCR extraction of inverter reading from display photo.
4. OCR result is stored with confidence and status.
5. Device GPS is stored with inverter reading capture.
6. Distance to site is calculated.
7. Geo validation status is stored.
8. API returns OCR + geo results for review/reporting.
9. Manual correction remains fallback only when OCR is unreadable or low-confidence.

---

## Notes for Codex

- Treat OCR as assistive automation with review path.
- For inverter registration, serial number is the most important extracted field.
- For service visit, cumulative reading is the most important extracted field.
- Keep registration OCR and reading OCR as separate flows/services.
- Do not couple this phase to Plant Performance Score.
