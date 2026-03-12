# Phase 1D / Phase 1E - Implementation Overview

## Current Naming
- **Phase 1D**: Inverter reading capture and generation foundation (implemented in this cycle)
- **Phase 1E**: Performance score, savings presentation, and visual reporting (planned next)

This replaces older wording that referred to "Phase 1D-A" and "Phase 1D-B".

## Why This Feature Exists
Solar EPC/AMC teams need visit proof plus measurable plant outcome:
- proof that each inverter was visited (photo evidence),
- cumulative inverter readings captured correctly,
- generation delta computed from prior accepted reading.

For MVP, this phase focuses on reliable operational truth in API/database first.

## Phase 1D Scope (Implemented)

### In scope
- Site inverter inventory configuration
- Work-order inverter listing driven by configured active inverters
- Inverter reading capture API with proof-photo linkage
- Baseline handling when no prior accepted reading exists
- Delta calculation for later visits
- Anomaly handling when current reading is lower than prior accepted reading
- Report-data API payload with generation totals and inverter-level details
- Functional automation for two-visit baseline-to-delta journey

### Out of scope in Phase 1D
- OCR extraction from inverter photos
- Firestore as system of record
- Tariff-based savings calculation and savings display
- Performance score
- Visual chart sections in reports
- Advanced telemetry/SCADA integrations

## Business Rules Used in Current Implementation

### Prior reading source
- Prior reading lookup uses **accepted/finalized** work orders:
  - `CUSTOMER_SIGNED`
  - `CLOSED`
- `SUBMITTED` alone is not treated as accepted baseline for delta.

### Baseline rule
- If prior accepted reading is missing:
  - `is_baseline = true`
  - `generation_delta_kwh = null`

### Delta rule
- If current reading >= prior accepted reading and inverter is operational:
  - `generation_delta_kwh = current - prior`

### Anomaly rule
- If current reading < prior accepted reading:
  - `is_anomaly = true`
  - `generation_delta_kwh = null`
  - negative generation is never emitted.

## Phase 1D Implemented Assets

### API endpoints used
- `POST /sites/{site_id}/inverters`
- `GET /sites/{site_id}/inverters`
- `PATCH /sites/{site_id}/inverters/{inverter_id}`
- `POST /workorders`
- `GET /workorders/{workorder_id}/inverters`
- `POST /workorders/{workorder_id}/inverter-readings`
- `POST /workorders/{workorder_id}/submit`
- `POST /workorders/{workorder_id}/send-approval`
- `POST /approve/{token}/sign`
- `GET /workorders/{workorder_id}/report-data`

### Core backend modules
- `backend/app/services/inverter_readings.py`
- `backend/app/services/report_summary.py`
- `backend/app/api/routes/workorders.py`

### Automation
- Local API suite:
  - `scripts/phase1d_local_api_tests.sh`
- Post-deploy stateful suite:
  - `scripts/phase1d_post_deploy_tests.sh`
- Functional orchestrator + modular scenarios:
  - `scripts/functional/run_phase1d_functional_suite.sh`
  - `scripts/functional/scenarios/uc_1d_001_setup_site_inventory.sh`
  - `scripts/functional/scenarios/uc_1d_002_visit1_capture_baseline.sh`
  - `scripts/functional/scenarios/uc_1d_003_visit2_capture_delta.sh`

## Phase 1E Scope (Planned)
- Savings model and tariff configuration UX/API
- Performance score with documented formula and snapshot behavior
- Visual reporting data model and rendering sections
- Report/PDF presentation enhancements for owner-facing value narrative

## Firestore Position (Decision for MVP)
- Postgres remains system of record.
- Firestore is not required for current Phase 1D implementation.
- Firestore may be revisited later only if real-time/offline sync requirements justify added operational complexity.
