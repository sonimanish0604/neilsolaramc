# NEIL Solar AMC SaaS (Mobile + Web + Supervisor Approval)

White-label Solar AMC checklist platform for Indian Solar EPCs.
Technicians complete AMC visits on mobile (offline-lite), capture photos, sign digitally, generate PDF reports,
and send an approval link to the customer site supervisor for final signature.

## Current Product Scope
- Frontend: FlutterFlow apps (Owner/Manager/Supervisor/Technician flows) and customer mobile web signing flow
- Backend: FastAPI (Cloud Run) + Cloud SQL Postgres + GCS media/report storage
- Auth: Firebase Auth
- Async: Cloud Run Jobs (migrations, report/signature processing, messaging tasks)
- Region target: `asia-south1` (Mumbai)

## Branching and Release Strategy (MVP)
Active long-lived branches:
- `develop` (active development + dev deploy)
- `main` (production release)

Rules:
- Work from feature branches: `feature/<short-name>`
- Every change via Issue + PR
- Promotion path: `feature/*` -> `develop` -> `main`

## CI/CD Baseline (Phase 0 complete)
- Cloud Build deploys from repo `cloudbuild.yaml`
- DB migrations run before service deploy via Cloud Run Job
- Post-deploy reports upload to `gs://neilsolar-ci-reports/...`
- `develop` runs full stateful post-deploy API tests
- `main` runs smoke-only post-deploy checks (`_RUN_STATEFUL_POST_DEPLOY_TESTS=false`)
- docs-only changes (`docs/**` and root `README.md`) use fast-path CI skip for build/deploy/test steps

## Phase Roadmap

### Phase 0 (Delivered)
Secure control-plane foundation:
- Firebase JWT verification
- Tenant/user/role model with tenant isolation
- Baseline audit logging and deployment automation

### Phase 1A (Delivered)
Core application-plane APIs and technician submission path:
- Customer and Site CRUD
- WorkOrder create/assign/list/status transitions
- Checklist submission (idempotent) + media metadata capture
- Technician signature ingestion (`PNG` contract)
- Tests for happy/rainy paths in CI and post-deploy

### Phase 1B (Delivered)
Approval and report completion path:
- PDF generation (tech-signed and customer-signed variants)
- Approval-link delivery via notification channel abstraction (Mailgun email operational for MVP)
- Tokenized approval flow with:
  - TTL = `72h`
  - single-use token after successful customer signature
- Final signed PDF regeneration and WorkOrder closure
- Branded/logo report layout

### Phase 1C (Delivered)
Stability and hardening:
- Retry and failure handling for async/report/messaging steps
- Approval token expiry/revocation and operational runbook coverage
- Stronger stateful post-deploy test coverage and regression gates
- Correlation IDs across critical flows (`workorder -> approval_event -> report_job`)

### Phase 1D (Delivered)
Inverter reading capture and generation foundation:
- Site inverter inventory APIs
- Workorder inverter reading capture with proof photo metadata
- Baseline/delta/anomaly generation computation
- Generation summary via `GET /workorders/{workorder_id}/report-data`
- Local + post-deploy + modular functional automation

### Phase 1E (Planned)
Evidence enrichment layer:
- Geo-validation for inverter capture evidence
- OCR-assisted inverter serial extraction (asset registration flow)
- OCR-assisted inverter reading extraction with review/correction path

### Phase 1F (Planned)
Reporting enrichment layer:
- Savings presentation (tariff-driven)
- Plant performance scoring
- Visual report sections/charts

## Checklist Extensibility Foundation (Future-proofing)
To support future verticals (solar, elevators, telecom towers, generators) without schema rewrites:
- Keep checklist definitions row-based (`checklist_templates`, `checklist_items`) instead of hardcoded columns.
- Persist answers in structured payload form (`checklist_responses.answers_json`) keyed by stable `item_key`.
- Allow tenant-specific template versions and optional additional fields over time.
- Preserve backward compatibility by versioning templates and storing `template_version` per response.

## Key Domain Entities (Simplified)

Control plane:
- `tenants`, `users`, `roles`, `invitations`, `plan_limits`, `audit_log`

Application plane:
- `customers`
- `sites` (including supervisor contact details)
- `checklist_templates`, `checklist_items`
- `work_orders`
- `checklist_responses`
- `media`
- `signatures` (`TECH`, `CUSTOMER_SUPERVISOR`)
- `reports`
- `approval_events` (token, expiry, opened/signed state)

WorkOrder lifecycle:
`SCHEDULED -> IN_PROGRESS -> SUBMITTED -> CUSTOMER_SIGNED -> CLOSED`

## Storage Strategy
- Do not store blobs in Postgres
- Store photos and PDFs in GCS buckets
- Store metadata, hashes, and object references in Postgres

## UI Flow References (FlutterFlow planning)
- `docs/solaramcapp-owner-login.drawio.png`
- `solaramcapp-manager-tasks.drawio.png`
- `solaramcapp-supervisor-tasks.drawio.png`
- `solaramcapp-customer-login.drawio.png`

## Canonical Docs
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT.md`
- `docs/DATA_MODEL.md`
- `docs/RUNBOOK.md`
- `docs/PRODUCT_VALUE_PROPOSITION.md`
- `docs/automate_strategy.md`
- `docs/AI_WORKFLOW_RULES.md`
- `docs/PHASE1A_LOCAL_TESTING.md`
- `docs/PHASE1_USE_CASE_TESTS.md`
- `docs/PHASE1B_CLOSURE_NOTE.md`
- `docs/PHASE1C_ACCOMPLISHMENTS_AND_NEXT_STEPS.md`
- `docs/phase1d/README.md`
- `docs/phase1d/Phase1d_PowerGenOverview.md`
- `docs/phase1e/phase1e_dbschema_api.md`
- `docs/phase1e/phase1e_geotag_and_ocr.md`

## Local Development
- Python 3.11+
- Docker
- Postgres (docker compose)

Typical commands:
- `make setup`
- `make dev`
- `make test`

## Ownership
Project: NEIL Solar
Author: Manish Soni
