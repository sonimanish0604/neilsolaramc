# Phase 1 Use Case Testing (Functional Scenarios)

Yes, this is functional testing in practical terms:
- Validate business flows end-to-end
- Not just single API endpoint checks

## Scope
This document adds scenario-based tests on top of:
- `docs/TEST_STRATEGY_PHASE1.md`
- `docs/TEST_CASES_PHASE1.md`
- `docs/PHASE1_USER_INTERACTION_FLOW.puml`

## Scenario Format
- `UC-ID`: stable use-case identifier
- `Goal`: what business outcome is validated
- `Preconditions`: required setup
- `Steps`: user/system journey
- `Expected Result`: business-level outcome
- `Coverage Mapping`: related API test case IDs/scripts

## Phase 1A Scenarios

### UC-1A-001 Tenant Onboarding (Admin Bootstrap)
- Goal: successfully onboard a tenant organization.
- Preconditions:
  - API is up
  - valid admin key configured
- Steps:
  1. Create tenant
  2. Create owner user
  3. Assign OWNER role
- Expected Result:
  - tenant exists
  - owner user exists in same tenant
  - owner role assigned
- Coverage Mapping:
  - `scripts/phase1a_local_api_tests.sh`
  - `scripts/ci_api_integration.sh`
  - `TEST_CASES_PHASE1`: `P1A-001`, `P1A-013`

### UC-1A-002 Owner Creates Customer and Site
- Goal: operational master data is ready for AMC execution.
- Preconditions:
  - owner context available (`AUTH_DISABLED=true` local dev user)
- Steps:
  1. Create customer
  2. Create site under customer
  3. List customers and sites
  4. Update customer and site
- Expected Result:
  - customer/site persisted and queryable
  - duplicate name checks enforced
  - updates reflected correctly
- Coverage Mapping:
  - `scripts/phase1a_local_api_tests.sh`
  - `scripts/ci_api_integration.sh`
  - `TEST_CASES_PHASE1`: `P1A-001`, `P1A-002`, `P1A-003`

### UC-1A-003 Technician Submission Path
- Goal: assigned technician can submit visit checklist and signature.
- Preconditions:
  - site/workorder exists
  - workorder assigned to technician
- Steps:
  1. Technician fetches assigned workorders
  2. Technician submits checklist + mandatory net meter media
  3. Technician signature PNG is submitted
- Expected Result:
  - workorder becomes `SUBMITTED`
  - checklist/net meter/media/signature records created
  - validation rules enforced (required media, max photos, PNG signature)
- Coverage Mapping:
  - `backend/tests/test_phase1a_validations.py`
  - `TEST_CASES_PHASE1`: `P1A-006`, `P1A-008`, `P1A-010`, `P1A-011`

## Phase 1B Scenarios (Delivered Baseline)

### UC-1B-001 Customer Approval Link Success
- Goal: customer signs through tokenized link and report finalizes.
- Preconditions:
  - submitted workorder
  - approval event created and not expired
- Steps:
  1. Customer opens tokenized link
  2. Customer signs with PNG signature
  3. System generates final PDF and closes workorder
- Expected Result:
  - token is consumed (single-use)
  - final report exists
  - workorder moves to `CUSTOMER_SIGNED` then `CLOSED`
- Coverage Mapping:
  - `TEST_CASES_PHASE1`: `P1B-001` ... `P1B-008`

### UC-1B-002 Token Expiry/Reuse Protection
- Goal: prevent invalid approval actions.
- Preconditions:
  - token exists
- Steps:
  1. attempt sign with expired token
  2. attempt reuse after successful sign
- Expected Result:
  - both actions rejected with proper response
- Coverage Mapping:
  - `TEST_CASES_PHASE1`: `P1B-005`, `P1B-006`

## Phase 1C Scenarios (Implemented)

### UC-1C-001 Retry and Recovery Path
- Goal: transient delivery/report failures recover cleanly.
- Coverage Mapping:
  - `scripts/phase1c_local_api_tests.sh`
  - `scripts/phase1c_post_deploy_tests.sh`
  - `TEST_CASES_PHASE1`: `P1C-001`, `P1C-002`, `P1C-007`, `P1C-010`

### UC-1C-002 Auditability and Safety
- Goal: critical lifecycle events are traceable and isolated by tenant.
- Coverage Mapping:
  - `scripts/phase1c_local_api_tests.sh`
  - `scripts/phase1c_post_deploy_tests.sh`
  - `TEST_CASES_PHASE1`: `P1C-006`, `P1C-009`, `P1C-011`, `SEC-001` ... `SEC-005`

## Execution Guidance
- Local functional run:
  - `bash scripts/phase1a_local_api_tests.sh`
- Reusable modular runner:
  - `bash scripts/functional/run_functional_suite.sh`
- Post-deploy functional checks:
  - `scripts/post_deploy_cloud_tests.sh` (always runs preflight checks)
  - stateful UC scenarios run when `RUN_STATEFUL_POST_DEPLOY_TESTS=true`
  - phase1c stateful checks run when `RUN_PHASE1C_POST_DEPLOY_TESTS=true`

### Modular Automation Layout
- `scripts/functional/lib/common.sh`
- `scripts/functional/scenarios/uc_1a_001_tenant_onboarding.sh`
- `scripts/functional/scenarios/uc_1a_002_customer_site_flow.sh`
- `scripts/functional/scenarios/uc_1a_003_tech_submit_validation.sh`
- `scripts/functional/run_functional_suite.sh`

Note:
- `UC-1A-002` requires authenticated application-user API access.
- Provide `FUNCTIONAL_BEARER_TOKEN` to run it in auth-enabled environments.

## Definition of Done for Use-Case Testing (Phase 1A)
- UC-1A-001, UC-1A-002 pass in local run and CI run.
- UC-1A-003 validation rules pass in automated tests.
- No P0/P1 failures in mapped test cases.
