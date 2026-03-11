# Phase 1C Accomplishments and Next Steps

Date: 2026-03-10  
Status: In Progress (Major hardening slice delivered)

## Scope Framing
This note aligns with `docs/README.md` roadmap for Phase 1C:
- Retry and failure handling for async/report/messaging
- Approval token expiry/revocation operational hardening
- Stronger stateful post-deploy regression gates

It also preserves MVP focus:
- Solar vertical remains primary delivery scope
- Architecture remains extensible for additional verticals later

## What Was Delivered in Phase 1C

1. Approval flow resilience and lifecycle hardening:
- Explicit token lifecycle handling with defensive checks (`EXPIRED`, `SIGNED`, `SUPERSEDED`, etc.)
- `send-approval`, `resend-approval` (`NEW_TOKEN`/`EXTEND`), and reminder run APIs
- Reminder and resend behavior with TTL renewal strategy and controlled retries

2. Messaging failure handling with provider classification:
- Retryable vs permanent provider failure classification
- Retry scheduling only for retryable failures
- Permanent failures marked and surfaced for operator/manual recovery

3. Async report job framework with retries:
- New `report_jobs` table and state machine (`QUEUED`, `RUNNING`, `FAILED`, `DEAD`, `SUCCEEDED`)
- Idempotency key support
- Retry/backoff and manual retry API behavior
- Approval-sign final report path moved to report-job pipeline for consistent retry semantics

4. Correlation ID traceability for troubleshooting:
- Request-level correlation middleware (`X-Correlation-ID` in/out)
- Correlation IDs persisted on `approval_events` and `report_jobs`
- Correlation ID propagated workorder -> approval event -> report job path

5. Stateful regression gates (local + post-deploy):
- Automated Phase 1C scripts added for local and cloud post-deploy validation
- API idempotency checks (repeat call behavior)
- Token supersession assertions (`NEW_TOKEN` invalidates old token)
- Retry/backoff assertions (simulated transient report failure then retry success)

6. Contact-channel readiness at site level:
- `site_supervisor_email` support added
- Validation ensures at least one supervisor contact channel (phone or email)

## MVP Decisions Confirmed

1. Vertical strategy:
- Keep production MVP focused on solar workflows.
- Maintain template/event/report abstractions to enable additional verticals later without major schema rewrite.

2. Email provider strategy:
- Mailgun is operational and used for MVP execution.
- SendGrid integration is intentionally parked for now and can be added as a secondary provider in a later phase.

3. Tenant customization direction:
- `checklist_templates`, `checklist_items`, and versioned responses remain the extensibility base.
- Per-tenant checklist field expansion is deferred to next phase to avoid MVP scope creep.

## Coverage Against Phase 1C Goals in README

1. Retry/failure handling for async/report/messaging: Mostly covered
- Implemented: approval and report retries, classification, and backoff.
- Pending: jitter tuning, DLQ-style replay workflows, queue SLO alerting.

2. Approval expiry/revocation runbook hardening: Substantially covered
- Implemented: lifecycle enforcement, resend/supersede behavior, reminder flows.
- Pending: deeper operator runbooks and revocation administrative tooling.

3. Stronger post-deploy stateful gates: Covered
- Implemented: stateful Phase 1C scripts with idempotency and failure-path assertions.

## Next Steps (Recommended)

1. Documentation cleanup and sync:
- Consolidate notification/report hardening details into canonical architecture + runbook docs.
- Keep this file and `PHASE1B_CLOSURE_NOTE.md` as phase-level status references.

2. Checklist per-tenant customization (next phase):
- Add owner/supervisor API flow for tenant-specific template cloning/versioning.
- Ensure backward compatibility for old template versions in historical reports.

3. Provider expansion (post-MVP):
- Add SendGrid as secondary email provider behind current provider-routing abstraction.
- Add provider health/failover policy and operational metrics.

4. Operations hardening continuation:
- Add alert thresholds and dashboard views for `DELIVERY_FAILED`, `DELIVERY_PERMANENT_FAILED`, and `DEAD` report jobs.
- Add explicit replay runbook and secured operator endpoints.

5. Security hardening continuation:
- Enforce managed secret providers by environment policy (dev/stage/prod).
- Reduce fallback secret resolution paths where not needed.
