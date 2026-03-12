# Phase 1 Test Strategy (1A, 1B, 1C, 1D)

## Purpose
Define a practical, CI/CD-aligned testing strategy for Phase 1 delivery milestones:
- Phase 1A: core application-plane workflows
- Phase 1B: customer approval + report completion
- Phase 1C: reliability hardening
- Phase 1D: inverter capture + generation foundation

This strategy follows `docs/AI_WORKFLOW_RULES.md` and current deployment baseline (`develop` and `main` branches).

## Scope
In scope:
- API contracts and state transitions
- DB migration safety and data integrity
- Media/signature/report generation flows
- approval-link lifecycle across configured notification channels
- Post-deploy validation in Cloud Build

Out of scope for now:
- FlutterFlow UI automation
- full load/performance testing
- multi-region failover

## Environments and Responsibilities
- Local: developer validation, unit tests, focused API integration tests.
- PR/CI (`develop`, `main`): lint + unit + integration-compose.
- Post-deploy `develop`: blocking smoke + stateful API regression suite.
- Post-deploy `main`: blocking smoke-only checks (current MVP policy).

## Test Levels
1. Static and unit tests
- Ruff lint
- Service/business-rule unit tests
- Schema/model validation tests

2. Integration/API tests
- API tests against app + DB
- migration tests for schema-dependent endpoints
- auth/role/tenant isolation checks

3. Post-deploy tests (Cloud Run URL)
- health and readiness checks
- stateful end-to-end API journey checks (on `develop`)
- smoke-only checks (on `main`)

4. Manual exploratory checks
- mobile-client compatible payload checks (checklist/signature/media metadata)
- approval link behavior on mobile browser

## Data Strategy
- Use tenant-scoped fixture data only.
- Each test run creates unique identifiers to avoid collisions.
- Keep destructive tests limited to test fixtures created during the same run.

## Phase 1A Strategy
Focus:
- customers/sites/workorders/checklist submission + tech signature

Required automated coverage:
- happy-path CRUD and lifecycle transitions
- rainy-path validation/auth failures (400/401/403/404/409)
- idempotent checklist submit behavior
- tenant isolation and role-based access

Exit criteria:
- all required CI checks pass
- post-deploy stateful suite on `develop` passes
- no migration regression in deploy pipeline

## Phase 1B Strategy
Focus:
- approval token workflow, notification delivery, signed report completion

Required automated coverage:
- token creation, open, sign, expiry, and single-use semantics
- TTL enforcement at 72h
- provider integration tests with mock/fake in CI and controlled dev validation
- PDF generation (pre-sign + final signed versions)
- workorder status transition to `CUSTOMER_SIGNED`/`CLOSED`

Exit criteria:
- deterministic token lifecycle behavior
- successful final signed PDF path and report record persistence
- no duplicate customer-sign acceptance after token use

## Phase 1C Strategy
Focus:
- reliability, retries, and operational hardening

Required automated coverage:
- retry behavior for transient notification/report generation failures
- duplicate webhook/request protection and idempotency behavior
- expiry/revocation operational scenarios
- stronger post-deploy regression suite across critical workflows
- correlation ID propagation checks across key APIs

Exit criteria:
- failure handling and recovery paths validated
- runbook-aligned diagnostics available for common incident classes

## Phase 1D Strategy
Focus:
- inverter inventory-driven capture
- baseline/delta/anomaly computation quality
- API-level generation summary correctness

Required automated coverage:
- local stateful API flow (`scripts/phase1d_local_api_tests.sh`)
- post-deploy stateful API flow (`scripts/phase1d_post_deploy_tests.sh`)
- modular functional journey (`scripts/functional/run_phase1d_functional_suite.sh`)
- service-level generation-rule tests (`backend/tests/test_phase1d_generation_rules.py`)

Exit criteria:
- baseline visit returns zero generation total and baseline flags
- second finalized visit returns expected positive deltas
- no negative generation emitted when readings regress

## Quality Gates by Branch
- PR to `develop`: lint + unit + integration-compose must pass.
- Push/merge to `develop`: Cloud Build deploy + migration + post-deploy tests must pass.
  - includes Phase 1C post-deploy suite when `_RUN_PHASE1C_POST_DEPLOY_TESTS=true`
- PR to `main`: same quality gates as `develop`.
- Push/merge to `main`: Cloud Build deploy + smoke checks must pass.

Docs-only optimization:
- If changes are restricted to `docs/**` and root `README.md`, pipeline fast-path skips build/deploy/test steps.
- Full pipeline can be forced via Cloud Build substitution `_FORCE_FULL_PIPELINE=true`.

## Reporting
Primary artifacts:
- pytest output and junit XML
- post-deploy summary markdown
- post-deploy junit XML
- post-deploy exit code

Cloud artifact target:
- `gs://neilsolar-ci-reports/<branch>/<service>/<build_id>/...`

## Defect Triage Priority
- P0: data loss, tenant data leak, auth bypass, broken deploy/migration
- P1: incorrect lifecycle state, signature/report corruption, token misuse
- P2: validation gaps, non-critical contract mismatches, low-impact regressions

## Future Branch Expansion
Current active branches remain `develop` and `main`.
When `test` and `staging` are introduced later, this strategy should be extended with:
- integration soak in `test`
- release-candidate sign-off in `staging`
