# Offline Mobile Capture Architecture
## Firestore + Cloud Storage + Backend API + Postgres

---

# Purpose

Define how the mobile app should support AMC field work in low-network or offline conditions while keeping Postgres as the final system of record.

This document explains:

- when Firestore should be used
- when Firestore should not be used
- how offline capture should work
- how photos should flow
- how data should move from Firestore to Postgres
- what finalization pipeline should be used for MVP

---

# Core Architecture Decision

## Final system of record
**Postgres** remains the authoritative source of truth for finalized business records.

Use Postgres for:
- tenants
- customers
- sites
- site inverter inventory
- confirmed inverter serial numbers
- finalized workorders
- finalized inverter readings
- geo-validation results
- OCR results accepted for business use
- generation calculations
- savings snapshots
- performance/report snapshots

## Offline/mobile workflow layer
**Firestore** is used only to support offline-first field execution.

Use Firestore for:
- mobile draft workorder state
- technician progress while on site
- local/offline capture staging
- sync queue state
- upload state for photos/files
- retry/error markers
- temporary draft OCR/geo status if needed for UX

## File storage
**Cloud Storage** stores:
- inverter label photos
- inverter display photos
- site/issue photos
- signatures
- generated PDFs if needed

---

# Architecture Decision Record
## ADR-P1E-OFFLINE-001 — Firestore as Offline Workflow Layer

Decision date: 2026-03-12

### Context
- Technicians may work in weak/no-network zones during AMC visits.
- Technicians may temporarily lose mobile data quota during active jobs.
- Evidence capture (photo + geo + OCR assist) must continue without blocking field work.
- Final business records still require normalized, auditable, tenant-isolated persistence.

### Decision
- Postgres remains the system of record for finalized operational truth.
- Firestore is introduced only for mobile offline draft/sync usability.
- Geo-tagging capture is allowed offline and validated when possible.
- ML Kit is used on-device for OCR assist (serial number and reading extraction UX), with backend as authoritative validator/persister.

### Offline Behavior Matrix

| Capability | Works offline? | Notes |
|---|---|---|
| Firestore draft writes | Yes | Mobile SDK caches writes locally and syncs later when connectivity returns. |
| Geo capture (device location) | Usually yes | GNSS/GPS can work without mobile data; availability/accuracy may vary by environment and device settings. |
| Geo validation | Partial offline + full on backend | App can capture location offline; backend computes authoritative status (`verified`, `outside_site_boundary`, `missing_device_location`, `geo_unverified`, etc.). |
| ML Kit OCR (on-device) | Yes | Prefer bundled model path for guaranteed first-run offline behavior. |
| ML Kit OCR (unbundled model) | Not guaranteed on first use | First model download requires network; after download, on-device inference can run offline. |
| Finalized evidence persistence | No (requires sync) | Final accepted records are committed to Postgres only after backend API validation. |

### Consequences
- Field operations are resilient to temporary network/data loss.
- Firestore draft state improves UX but does not weaken data governance.
- Retry/idempotency remains mandatory to prevent duplicate finalized evidence.
- Backend remains the decision point for compliance-grade evidence outcomes.

### Why This Decision Was Chosen
- Minimizes operational risk versus direct Firestore-to-Postgres mirroring.
- Keeps offline UX strong without compromising auditability.
- Supports phased rollout of OCR/geo capabilities while preserving existing lifecycle APIs.

### External Sources Used
Source verification date: 2026-03-12

- Firestore offline persistence:
  - https://firebase.google.com/docs/firestore/manage-data/enable-offline
  - https://firebase.google.com/docs/firestore/real-time_queries_at_scale
- ML Kit overview and installation behavior:
  - https://developers.google.com/ml-kit/guides
  - https://developers.google.com/ml-kit/tips/installation-paths
  - https://developers.google.com/ml-kit/vision/text-recognition/v2/android
- Android location behavior and requirements:
  - https://developer.android.com/develop/sensors-and-location/location/retrieve-current
  - https://developer.android.com/develop/sensors-and-location/location/change-location-settings

---

# When to Use Firestore

Use Firestore when the app needs to continue working even without network.

Examples:

- technician opens assigned workorder and continues checklist offline
- technician captures inverter photo while network is unavailable
- technician stores device GPS with capture event
- technician records draft visit progress
- app tracks whether a photo is:
  - pending upload
  - uploaded
  - validation pending
  - finalized
  - failed
- app needs fast mobile sync behavior when network returns

### Firestore is appropriate for
- draft data
- temporary sync state
- offline-first field workflow
- app-facing document state
- queue markers and retry markers

---

# When Not to Use Firestore

Do not use Firestore as the final business database for:

- confirmed inverter inventory master
- finalized accepted reading history
- report snapshot history
- authoritative geo-validation audit
- authoritative OCR audit
- generation rollups
- savings history
- scoring/reporting records
- cross-entity reporting queries

These belong in Postgres.

---

# Key Rule

## Firestore is not the final source of truth
Firestore is a **working layer**, not the final ledger.

Once a workorder or inverter reading is finalized, the normalized accepted record must live in Postgres.

---

# High-Level Flow

## Offline capture flow
1. technician opens workorder on mobile app
2. app loads workorder/site/inverter snapshot from local cache / Firestore
3. technician captures checklist data and photos offline
4. app stores draft state locally and in Firestore sync layer when possible
5. app marks records as pending upload / pending validation

## Online sync flow
6. when network becomes available, app uploads photos to Cloud Storage
7. app updates Firestore draft doc with uploaded file paths
8. app calls backend finalization/validation API
9. backend validates evidence, runs OCR/geo/business rules
10. backend writes finalized accepted records into Postgres
11. backend updates Firestore status to finalized / review_required / failed

---

# Recommended Pipeline for MVP

## Do not use Kafka for MVP
Kafka-style streaming is not needed yet.

Reasons:
- too much operational complexity
- your workflow is transactional and workorder based
- finalization is naturally API-driven
- retry logic can be handled with app state + backend job model

## Recommended MVP pipeline
Use a **request-driven finalization pipeline**.

### Pipeline steps
1. mobile captures draft data in Firestore
2. mobile uploads files to Cloud Storage
3. mobile calls backend finalization API
4. backend reads payload and validates referenced files
5. backend writes accepted records to Postgres inside controlled transaction boundaries
6. backend returns result
7. backend or app updates Firestore workflow status

This is simpler, safer, and easier for Codex to implement.

---

# Architecture Components

## Mobile App
Responsibilities:
- work offline
- capture draft data
- capture photos
- capture device GPS
- store sync state
- retry uploads
- call backend APIs when online

## Firestore
Responsibilities:
- hold draft workorder state
- hold temporary inverter capture state
- track photo upload status
- track validation/finalization state for UX
- support offline sync behavior

## Cloud Storage
Responsibilities:
- store photo binaries
- store signatures
- store PDFs if required

## Backend API
Responsibilities:
- validate payload completeness
- run OCR
- run geo-validation
- apply business rules
- create/update normalized Postgres records
- calculate generation/savings when applicable
- lock finalized evidence
- return review/failure/finalized outcomes

## Postgres
Responsibilities:
- store final accepted records
- preserve history
- support queries/reports
- support report snapshot generation

---

# Firestore Data Scope

## Recommended Firestore collections/documents

### work_order_drafts
Purpose:
Store draft workorder execution state for the technician.

Suggested fields:
- workorder_id
- tenantId
- site_id
- technicianUserId
- status
- startedAt
- lastModifiedAt
- syncStatus
- finalizationStatus

### inverter_capture_drafts
Purpose:
Store per-inverter draft capture state.

Suggested fields:
- workorder_id
- inverterId
- serialNumber
- localPhotoPath
- cloudPhotoPath
- uploadStatus
- deviceLatitude
- deviceLongitude
- deviceAccuracyMeters
- capturedAt
- draftOperationalStatus
- draftRemarks
- ocrStatus
- geoStatus
- reviewRequired
- syncStatus

### upload_queue
Purpose:
Track pending uploads and retries.

Suggested fields:
- queueItemId
- entityType
- entityId
- localFilePath
- cloudStoragePath
- uploadStatus
- retryCount
- lastError
- updatedAt

---

# Firestore Status Model

Use Firestore to track workflow states.

## Example workorder statuses
- `draft`
- `capturing`
- `photo_pending_upload`
- `photo_uploaded`
- `pending_backend_validation`
- `review_required`
- `finalized`
- `sync_failed`

## Example upload statuses
- `pending`
- `uploading`
- `uploaded`
- `failed`
- `retrying`

## Example sync statuses
- `offline_only`
- `queued`
- `synced_to_backend`
- `backend_failed`

---

# Postgres Finalization Model

## Finalization rule
Only finalized or reviewable accepted records are persisted as authoritative operational records in Postgres.

### What goes to Postgres
- confirmed inverter inventory
- accepted reading evidence
- OCR audit rows
- geo-validation results
- finalized workorder reading rows
- generation totals
- report snapshots

### What stays in Firestore only
- abandoned drafts
- temporary upload states
- partial/incomplete capture data
- unsent retries
- ephemeral app UX state

---

# Synchronization Strategy

## Recommended strategy
Use **API-driven synchronization**, not direct Firestore-to-Postgres mirroring.

### Why
Direct mirroring causes problems:
- partial drafts pollute Postgres
- abandoned work leaks into final DB
- backend business rules may be bypassed
- duplicates are harder to control

## Better strategy
The app should explicitly request backend finalization after draft capture is sufficiently complete.

This means:
- Firestore is staging
- backend decides what becomes official
- Postgres only stores accepted finalized records

---

# Synchronization Pipeline

## Stage 1 - Offline capture
Mobile app writes draft state to Firestore and local cache.

## Stage 2 - Upload stage
When network is available:
- mobile uploads photos to Cloud Storage
- Firestore draft docs updated with cloud paths

## Stage 3 - Finalization request
Mobile app syncs inverter evidence to backend APIs.

Example:
- `POST /workorders/{workorder_id}/inverter-readings/from-photo` (per inverter evidence sync)
- `POST /workorders/{workorder_id}/submit` (existing lifecycle finalization step)

Payload may include:
- workorder_id
- list of inverter draft references
- cloud photo paths
- capture timestamps
- device location metadata
- technician remarks

## Stage 4 - Backend validation
Backend:
- verifies required files uploaded
- resolves site/inverter references
- runs OCR
- runs geo-validation
- applies review rules
- determines accepted reading values

## Stage 5 - Postgres commit
Backend writes normalized accepted records to Postgres.

Recommended:
- use transactions around logical finalization units where possible
- prevent duplicates using idempotency keys and unique constraints

## Stage 6 - Firestore status update
After backend result:
- Firestore workorder doc updated to `finalized`, `review_required`, or `sync_failed`
- per-inverter draft docs updated with backend result summary

---

# Should Backend Read Firestore Directly?

## Preferred MVP answer
No, not as the main pattern.

Preferred flow:
- app calls backend API with the needed payload/references
- backend uses Cloud Storage references and Postgres references
- backend may optionally use Firestore document ids as helper references, but should not depend on Firestore as final truth

## Why
This keeps the backend authoritative and avoids tight coupling between your final business logic and Firestore document structures.

---

# Optional Backend-Initiated Sync

If needed later, you may introduce a backend job that reads Firestore draft documents and processes “ready_to_finalize” items.

But this should be a later optimization, not the initial design.

### Later pattern could be
- Firestore document marked `ready_to_finalize`
- Cloud Function / backend worker triggered
- worker validates and writes to Postgres
- worker updates Firestore result state

This is acceptable later, but not required for MVP.

---

# Recommended MVP Choice

## Use explicit API-based finalization first
This is the simplest and safest choice.

### Benefits
- easier debugging
- easier idempotency
- easier business rule enforcement
- less hidden coupling
- clearer ownership between app, Firestore, backend, and Postgres

---

# Idempotency Requirements

Because mobile sync retries will happen, the backend must be idempotent.

## Minimum rules
- unique inverter reading per `workorder_id + inverter_id`
- inverter reading sync endpoint should safely handle retries
- repeated submit/finalization request must not create duplicate evidence rows
- repeated photo upload callback must not duplicate audit rows unnecessarily

---

# Error Handling

## Common failure cases
- photo not uploaded yet
- OCR failed
- GPS missing
- device outside site boundary
- network drops during finalization
- duplicate finalization request
- partial inverter completion

## Backend behavior
- return structured result
- preserve review_required states
- do not silently lose draft data
- do not create duplicate finalized records

---

# Suggested Finalization Outcomes

For each workorder or inverter evidence record, backend may return:

- `finalized`
- `review_required`
- `rejected`
- `partial_finalization`
- `sync_failed`

These outcomes can be reflected back into Firestore for mobile UX.

---

# Why Not Kafka Yet

Kafka or event streaming may become useful later if you have:
- very high scale
- many asynchronous downstream consumers
- analytics pipelines
- audit/event streaming requirements
- notification fanout

But for current MVP:
- too complex
- adds operational burden
- not required for workorder finalization
- not needed for OCR/geo pipeline

## Current recommendation
Use:
- Firestore
- Cloud Storage
- backend APIs
- Postgres
- optional async worker/job for OCR if needed

That is enough.

---

# Future Evolution Path

Later, if needed, you can evolve toward:

## Step 1
API-driven finalization

## Step 2
Background job processing for OCR/report generation

## Step 3
Event/outbox pattern from Postgres for downstream notifications

## Step 4
Message broker only if scale or architecture truly requires it

---

# Guidance to Codex

## Mandatory rules
1. Postgres remains final system of record.
2. Firestore is used only for offline/mobile draft and sync state.
3. Cloud Storage stores photo binaries.
4. Backend APIs own validation and finalization.
5. Do not directly mirror all Firestore documents into Postgres.
6. Finalized accepted records must be written to Postgres only after backend validation.
7. Design APIs and DB constraints to support retries safely.

## Recommended implementation order
1. define Firestore draft document shapes
2. define upload queue states
3. define backend finalization API
4. implement Cloud Storage upload references
5. implement Postgres persistence for finalized records
6. implement Firestore status updates after backend result
7. add retry-safe idempotency behavior

---

# Final Summary

Use Firestore because the mobile app must support AMC field work offline.

But use it only for:
- draft capture
- offline sync
- upload queue state
- mobile workflow status

Use Postgres for:
- final accepted business truth
- evidence history
- generation/reporting data

Use backend APIs as the bridge.

For MVP, use an API-driven finalization pipeline, not Kafka.
