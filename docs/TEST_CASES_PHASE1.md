# Phase 1 Test Cases (1A, 1B, 1C)

## Conventions
- Priority: `P0` (must block), `P1` (high), `P2` (medium)
- Type: `UNIT`, `INTEGRATION`, `POST_DEPLOY`, `MANUAL`
- Status values in expected results follow current lifecycle:
  `SCHEDULED -> IN_PROGRESS -> SUBMITTED -> CUSTOMER_SIGNED -> CLOSED`

## Phase 1A Test Cases

| ID | Priority | Type | Scenario | Expected Result |
|---|---|---|---|---|
| P1A-001 | P0 | INTEGRATION | Create customer with valid tenant/role | `201`, record created under tenant |
| P1A-002 | P0 | INTEGRATION | Create duplicate customer identifier rule | `409` conflict behavior enforced |
| P1A-003 | P0 | INTEGRATION | Create site under customer | `201`, site linked to customer |
| P1A-004 | P0 | INTEGRATION | Access customer/site from another tenant | `404` or `403`, no cross-tenant leak |
| P1A-005 | P0 | INTEGRATION | Create workorder and assign technician | `201`, status `SCHEDULED` |
| P1A-006 | P0 | INTEGRATION | Technician lists assigned workorders | only assigned workorders returned |
| P1A-007 | P0 | INTEGRATION | Invalid lifecycle transition (e.g. `SCHEDULED` -> `CLOSED`) | `400` and no state change |
| P1A-008 | P0 | INTEGRATION | Submit checklist response with required fields | `200/201`, status moves to `SUBMITTED` |
| P1A-009 | P0 | INTEGRATION | Re-submit same checklist payload with idempotency key | no duplicate records; deterministic response |
| P1A-010 | P0 | INTEGRATION | Submit net meter section missing mandatory fields/photo | `400` validation error |
| P1A-011 | P1 | INTEGRATION | Submit technician signature PNG payload | signature stored and linked to workorder |
| P1A-012 | P1 | UNIT | Pass/fail counting logic | counts match checklist rules |
| P1A-013 | P1 | INTEGRATION | Role access guard (TECH tries owner-only endpoint) | `403` forbidden |
| P1A-014 | P1 | POST_DEPLOY | Stateful journey on `develop` | create -> assign -> submit passes end to end |
| P1A-015 | P2 | MANUAL | Mobile-compatible payload formatting check | payload accepted without contract drift |

## Phase 1B Test Cases

| ID | Priority | Type | Scenario | Expected Result |
|---|---|---|---|---|
| P1B-001 | P0 | INTEGRATION | Generate approval token on submit | token created with status `SENT`, expiry set |
| P1B-002 | P0 | INTEGRATION | Token expiry policy | `expires_at = created_at + 72h` |
| P1B-003 | P0 | INTEGRATION | Open approval link before expiry | allowed, status transitions to `OPENED` |
| P1B-004 | P0 | INTEGRATION | Customer submits signature with valid token | accepted, customer signature stored |
| P1B-005 | P0 | INTEGRATION | Reuse same token after successful sign | rejected (single-use), no second signature |
| P1B-006 | P0 | INTEGRATION | Use expired token | rejected with expiry-specific response |
| P1B-007 | P0 | INTEGRATION | Final signed PDF generation after customer sign | final report persisted with `is_final=true` |
| P1B-008 | P0 | INTEGRATION | Workorder close after customer sign | state reaches `CUSTOMER_SIGNED` then `CLOSED` |
| P1B-009 | P1 | UNIT | Token generator uniqueness/entropy checks | no collisions in test batch |
| P1B-010 | P1 | INTEGRATION | Notification send success path (configured provider) | approval event logged as delivered/sent |
| P1B-011 | P1 | INTEGRATION | Notification failure path (configured provider) | failure logged with retry/permanent classification |
| P1B-012 | P1 | MANUAL | Report branding/logo rendering | report layout matches approved template |
| P1B-013 | P1 | POST_DEPLOY | Full approval flow on `develop` | submit -> link open -> sign -> close passes |
| P1B-014 | P2 | MANUAL | Mobile browser sign flow usability | signature capture succeeds on phone viewport |
| P1B-015 | P1 | POST_DEPLOY | Notification email smoke in deployed env | `/notifications/trysendemail` returns `200` with provider response |

Phase 1B automation mapping:
- `P1B-002`, `P1B-005`, `P1B-009`, `P1B-011`: `backend/tests/test_phase1b_services.py`
- `P1B-003`, `P1B-004`, `P1B-005`: `scripts/functional/scenarios/uc_1b_001_approval_token_flow.sh`
- `P1B-013`: `scripts/post_deploy_cloud_tests.sh` with `RUN_PHASE1B_APPROVAL_SCENARIO=true`
- `P1B-015`: `scripts/functional/scenarios/uc_1b_002_notification_email_smoke.sh` via:
  - local: `scripts/phase1b_local_api_tests.sh`
  - cloud: `scripts/post_deploy_cloud_tests.sh` with `RUN_PHASE1B_NOTIFICATION_SMOKE=true`

## Phase 1C Test Cases

| ID | Priority | Type | Scenario | Expected Result |
|---|---|---|---|---|
| P1C-001 | P0 | INTEGRATION | Retry report generation on transient error | retries occur, eventually succeeds or marks failed cleanly |
| P1C-002 | P0 | INTEGRATION | Retry notification send on transient error | bounded retries with clear terminal state |
| P1C-003 | P0 | INTEGRATION | Duplicate delivery callback/request | idempotent handling, no duplicate state mutation |
| P1C-004 | P0 | INTEGRATION | Token revocation before use | access denied after revocation |
| P1C-005 | P1 | POST_DEPLOY | Expanded regression suite on `develop` | critical journeys pass in one run |
| P1C-006 | P1 | INTEGRATION | Audit log completeness for critical events | create/send/open/sign/close events captured |
| P1C-007 | P1 | MANUAL | Runbook drill for failed approval send | operator can diagnose and recover |
| P1C-008 | P2 | INTEGRATION | Non-critical data mismatch in report metadata | error surfaced without crashing flow |
| P1C-009 | P0 | INTEGRATION | `NEW_TOKEN` resend supersedes previous token | old token rejected (`410`), new token valid |
| P1C-010 | P0 | INTEGRATION | Report job retry/backoff | first attempt fails, `next_retry_at` set, retry can succeed |
| P1C-011 | P1 | INTEGRATION | Correlation ID propagation | response/body correlation IDs present and traceable |

## Cross-Phase Security and Data Isolation Cases

| ID | Priority | Type | Scenario | Expected Result |
|---|---|---|---|---|
| SEC-001 | P0 | INTEGRATION | JWT missing/invalid | `401` |
| SEC-002 | P0 | INTEGRATION | User without role attempts write operation | `403` |
| SEC-003 | P0 | INTEGRATION | Tenant A accesses Tenant B workorder/report | blocked with no leakage |
| SEC-004 | P1 | INTEGRATION | Signature file type mismatch | validation failure |
| SEC-005 | P1 | INTEGRATION | Oversized media metadata/photo count > plan limit | rejected with clear error |

## Suggested Automation Mapping
- Unit tests: `backend/tests/unit/*`
- Integration tests: `backend/tests/integration/*`
- Post-deploy suite driver: `scripts/post_deploy_cloud_tests.sh`
- JUnit and summary artifacts uploaded to CI and GCS report bucket
