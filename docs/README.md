# NEIL Solar AMC SaaS (Mobile + Web + WhatsApp Approval)

White-label Solar AMC checklist platform for Indian Solar EPCs.
Techs complete AMC visits on mobile (offline-lite), capture photos, sign digitally, generate PDF report,
and send WhatsApp approval link to the customer site supervisor who signs on phone.

Stack:
- Mobile/Web UI: FlutterFlow (client)
- Auth: Firebase Auth
- Backend API: FastAPI (Python)
- DB: Cloud SQL Postgres (GCP)
- Media/PDF: Google Cloud Storage (GCS)
- Async Jobs: Cloud Run Jobs (or Cloud Tasks + worker)
- IaC: Terraform (GCP)

Data residency target: India (GCP region asia-south1 / Mumbai).

---

## Branching strategy (Git)
We use 4 long-lived branches:
- develop: active development
- test: integration testing (QA, smoke tests)
- staging: production-like, pre-release validation
- main: live production releases

Rules:
- Work is done in feature branches: feature/<short-name>
- Every change uses an Issue + PR
- Merge order: develop -> test -> staging -> main
- Tag releases on production: vX.Y.Z

---

## High-level architecture

Clients
- FlutterFlow Technician Mobile App (Android first; iOS supported)
- FlutterFlow Owner/Supervisor Web Portal
- Customer Supervisor: no app required (tokenized mobile web approval link)

Backend (Application Plane)
- FastAPI REST API (Cloud Run)
- Postgres (Cloud SQL): tenant-safe relational model
- GCS bucket: photos + PDFs; Postgres stores metadata + hashes + URLs

Control Plane (SaaS)
- Tenant (Organization) management
- User + Role-based access control (Owner/Supervisor/Tech/Customer)
- Plan limits (max customers/sites/users/photos; retention days)
- Telemetry events (basic)

Async
- Report generation (HTML -> PDF)
- WhatsApp approval link delivery
- Retention cleanup (delete expired PDFs/photos)

---

## Phase plan (build order)

### Phase 0 — Minimum control-plane skeleton (MUST HAVE)
Goal: secure multi-tenant foundation, minimal friction.
- Firebase Auth integration (JWT verification in FastAPI)
- Tenant + Users + Roles + tenant isolation (tenant_id everywhere)
- Basic admin endpoints (create tenant/users manually for pilot)
- Audit log table (append-only)

### Phase 1 — Application plane MVP (THE PRODUCT)
Goal: end-to-end flow works.
Owner/Supervisor (web):
- CRUD Customers, Sites
- Create WorkOrders (AMC visits), assign technician
Technician (mobile):
- List assigned WorkOrders
- Offline-lite checklist execution + photo capture (max 20)
- Technician signature
Backend:
- Submit checklist response + media metadata
- Generate PDF report
- Send WhatsApp approval link (tokenized)
Customer Supervisor:
- Open link, view summary + PDF, sign digitally on phone
- Backend regenerates final signed PDF, closes workorder

### Phase 2 — SaaS hardening
- Self-serve tenant onboarding + invitations
- Plan limits enforced across endpoints
- Telemetry + basic admin dashboard
- Rate limiting + abuse protection

### Phase 3 — Billing + advanced compliance
- Payments + invoices
- Full SOC2/ISO27001 evidence program (optional based on customer demand)

---

## Key domain entities (simplified)

Control Plane:
- tenants, users, roles, invitations, plan_limits, audit_log

Application Plane:
- customers
- sites (with site_supervisor_name + site_supervisor_phone)
- checklist_templates + checklist_items (same template for all sites)
- work_orders (AMC visits)
- checklist_responses (JSON)
- media (photos)
- signatures (TECH + CUSTOMER_SUPERVISOR)
- reports (pdf_url + hash + pass/fail counts)
- approval_events (whatsapp token, expiry, opened/signed)

WorkOrder lifecycle:
SCHEDULED -> IN_PROGRESS -> SUBMITTED -> CUSTOMER_SIGNED -> CLOSED

---

## Storage strategy (cost + performance)
- DO NOT store blobs in Postgres.
- Photos/PDFs go to GCS.
- Postgres stores metadata + signed URLs + sha256 hashes.

Signed URL access is preferred to reduce backend egress and CPU.

---

## GCP deployment (Terraform-managed)

Target region: asia-south1 (Mumbai)

Resources:
- Cloud Run service: all-solar-api (FastAPI)
- Cloud Run job: report-worker (PDF generation, WhatsApp sends, retention cleanup)
- Cloud SQL Postgres: neil-solar-postgres
- GCS buckets:
  - neil-solar-media (photos)
  - neil-solar-reports (pdfs)
- Secret Manager:
  - DATABASE_URL or DB credentials
  - WhatsApp provider creds
  - JWT config (Firebase project details as needed)

Environments:
- dev, test, staging, prod (each has its own Cloud Run + Cloud SQL + buckets)
- Use separate GCP projects for staging/prod if possible; otherwise separate naming + IAM boundaries.

---

## Repo structure

See /docs for architecture, threat model, and operational playbooks.

## Delivery Automation

- See `docs/automate_strategy.md` for the canonical automation checklist (local testing, PR checks, merge/deploy gates).
- See `docs/testing_strategy.puml` for the visual flow diagram.

---

## Local development
- Python 3.11+
- Docker
- Postgres local (docker compose)

Commands:
- make setup
- make dev
- make test

---

## Compliance posture (SOC2/ISO27001-ready engineering)
We implement:
- Audit logging
- RBAC
- Secrets management
- Backups and retention
- PR-based change control

We do NOT implement full certification evidence collection until customer demand requires it.

---

## Ownership
Project: NEIL Solar
Author: Manish Soni
