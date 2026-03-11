# GCP Cloud Run Deployment (Current MVP)

This repository deploys API workloads to Cloud Run using Cloud Build (`cloudbuild.yaml`).

## Active Services
- Dev: `neilsolar-dev-api` (from `develop`)
- Prod: `neilsolar-prod-api` (from `main`)

## Core Artifacts
- Artifact Registry repository for backend images
- Cloud SQL Postgres
- GCS buckets for media/reports
- Secret Manager for runtime and DB credentials
- Cloud Run Job for DB migrations

## Build/Deploy Flow
1. Build image
2. Push image
3. Run DB migrations via Cloud Run Job
4. Deploy Cloud Run service
5. Run smoke/post-deploy checks
6. Upload test reports to GCS

## Trigger Strategy
- Trigger 1: `develop` -> deploy Dev service
- Trigger 2: `main` -> deploy Prod service

## Post-deploy Test Modes
- Dev: stateful post-deploy tests enabled
- Prod: smoke-only by default

## Docs-only Fast Path
- Cloud Build classifies docs-only changes (`docs/**` + root `README.md`) and skips build/deploy/test steps.
- Override controls:
  - `_DOCS_ONLY_OVERRIDE=true|false|auto`
  - `_FORCE_FULL_PIPELINE=true` to force full execution

## Recommended Variables
- `PROJECT_ID`
- `REGION=asia-south1`
- `AR_REPO`
- `_SERVICE`
- `_RUNTIME_SA`
- `_DB_URL_SECRET`
- `_DB_ADMIN_SECRET`
- `_RUN_STATEFUL_POST_DEPLOY_TESTS`
- `_RUN_PHASE1C_POST_DEPLOY_TESTS`

## Future Expansion (Deferred)
`test` and `staging` services/triggers are intentionally deferred and can be introduced later.
