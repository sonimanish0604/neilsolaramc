# Deployment (Current MVP)

## Region
- `asia-south1` (Mumbai)

## Active Environments (MVP)
We currently deploy two active environments in one GCP project:
- `dev` (`develop` branch)
- `prod` (`main` branch)

Branch mapping:
- `develop` -> `neilsolar-dev-api`
- `main` -> `neilsolar-prod-api`

## Build and Deploy Path
- Cloud Build builds and pushes container image
- DB migrations run before service deploy via Cloud Run Job
- Cloud Run service deploy is executed from `cloudbuild.yaml`

## Per-environment Resources
Cloud Run:
- `neilsolar-<env>-api`

Cloud SQL:
- env-specific instance/credentials (secrets-backed)

GCS buckets:
- `neilsolar-<env>-media`
- `neilsolar-<env>-reports`

Secret Manager:
- `DATABASE_URL`
- `DATABASE_ADMIN_URL`
- provider and runtime secrets by environment

Service accounts:
- runtime API/service account per environment
- migration job/service account per environment

## Worker/Async Behavior
- Report generation through async report-job APIs
- Approval delivery via channel abstraction (email/whatsapp)
- Retention cleanup via scheduled maintenance jobs

## Post-deploy Validation
- `develop`: stateful post-deploy API checks (including Phase 1C suite when enabled)
- `main`: smoke-only post-deploy checks (current MVP release policy)

## Future Expansion (Deferred)
`test` and `staging` can be introduced later if release governance needs additional promotion stages.
