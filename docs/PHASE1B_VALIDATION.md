# Phase 1B Validation (Local + Cloud)

Use this playbook to validate Phase 1B without waiting for Phase 1C hardening.

Detailed list of local Phase 1B tests and checks:
- `docs/PHASE1B_LOCAL_TEST_INVENTORY.md`

## Scope for Phase 1B Validation

- Approval token flow (`72h` TTL, single-use semantics)
- Customer signature submission flow
- Notification email smoke via `/notifications/trysendemail`
- Notification/unit service checks that already exist in `backend/tests/*`

Phase 1C hardening (retry architecture deepening, lock-safe dequeue, dead-letter ops runbooks) remains separate.

## 1) Local Laptop Validation

Run from repo root:

```bash
bash scripts/phase1b_local_api_tests.sh
```

This performs:
- Docker compose startup (`api`, DB, notification services)
- Targeted pytest suite for Phase 1B + notification engine modules
- Functional scenarios:
  - `uc_1b_001_approval_token_flow`
  - `uc_1b_002_notification_email_smoke`

Artifacts:
- `reports/phase1b-local/summary.md`
- `reports/phase1b-local/pytest_output.txt`
- `reports/phase1b-local/pytest_junit.xml`
- `reports/phase1b-local/functional/summary.md`
- `reports/phase1b-local/functional/junit.xml`

### Optional env for local run

- `FUNCTIONAL_APPROVAL_TOKEN=<token>` for `UC-1B-001` (else it is skipped)
- `FUNCTIONAL_PHASE1B_EMAIL_TO=<recipient@email>` for `UC-1B-002` (else it is skipped)
- `FUNCTIONAL_PHASE1B_DOMAIN_SELECTOR=1|2`
- `FUNCTIONAL_PHASE1B_EMAIL_FROM=<from@email>`
- `RUN_PHASE1B_PYTEST=true|false`
- `APPROVAL_BASE_URL=http://localhost:8080/approve` (recommended for local link testing)
- `REPORT_STORAGE_BACKEND=AUTO|LOCAL|GCS`
- `LOCAL_REPORTS_DIR=/tmp/neilsolar-reports`

## 2) Cloud Post-Deploy Validation (GCP)

`scripts/post_deploy_cloud_tests.sh` supports an additional toggle:

- `RUN_PHASE1B_NOTIFICATION_SMOKE=true`

Required when enabled:
- `FUNCTIONAL_PHASE1B_EMAIL_TO=<recipient@email>`

Optional:
- `FUNCTIONAL_PHASE1B_DOMAIN_SELECTOR=1|2`
- `FUNCTIONAL_PHASE1B_EMAIL_FROM=<from@email>`
- `FUNCTIONAL_PHASE1B_EMAIL_SUBJECT=...`
- `FUNCTIONAL_PHASE1B_EMAIL_TEXT=...`

`cloudbuild.yaml` substitutions added:
- `_RUN_PHASE1B_APPROVAL_SCENARIO`
- `_FUNCTIONAL_APPROVAL_TOKEN`
- `_FUNCTIONAL_CUSTOMER_SIGNER_NAME`
- `_FUNCTIONAL_CUSTOMER_SIGNER_PHONE`
- `_FUNCTIONAL_CUSTOMER_SIGNATURE_OBJECT_PATH`
- `_RUN_PHASE1B_NOTIFICATION_SMOKE`
- `_PHASE1B_EMAIL_TO`
- `_PHASE1B_DOMAIN_SELECTOR`
- `_PHASE1B_EMAIL_FROM`
- `_PHASE1B_EMAIL_SUBJECT`
- `_PHASE1B_EMAIL_TEXT`

When `_RUN_PHASE1B_NOTIFICATION_SMOKE=true`, Cloud Build runs `UC-1B-002` in the post-deploy functional suite.

## 3) Report Link Behavior (Local vs GCP)

Approval email payload includes:
- `approval_url`: `.../approve/{token}`
- `report_url`: `.../approve/{token}/report`

`/approve/{token}/report` is token-gated and serves PDF bytes.
- local laptop: PDFs are stored under `LOCAL_REPORTS_DIR` and streamed from API
- Cloud Run: with `REPORT_STORAGE_BACKEND=AUTO`, service uses GCS bucket storage and streams via API

Example:

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_RUN_PHASE1B_NOTIFICATION_SMOKE=true,_PHASE1B_EMAIL_TO=manish.soni@nogginhausenergy.org,_PHASE1B_DOMAIN_SELECTOR=1
```

Approval-flow example:

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_RUN_PHASE1B_APPROVAL_SCENARIO=true,_FUNCTIONAL_APPROVAL_TOKEN=<fresh-token>
```
