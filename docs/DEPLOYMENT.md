# Deployment

## Region
India: asia-south1 (Mumbai)

## Single GCP project, multi-env resources
We deploy 4 environments into one GCP project using strict naming + separate service accounts:
- dev
- test
- staging
- prod

## Cloud Run continuous deployment
Use “Continuously deploy from a repository” in Cloud Run.

Branch mapping:
- develop → neilsolar-dev-api
- test → neilsolar-test-api
- staging → neilsolar-staging-api
- main → neilsolar-prod-api

Build strategy:
- Dockerfile-based build (recommended)
- Artifact Registry stores built images

## Per-environment resources (recommended)
Cloud Run:
- neilsolar-<env>-api
Cloud SQL:
- neilsolar-<env>-db (Postgres)
GCS buckets:
- neilsolar-<env>-media
- neilsolar-<env>-reports
Secrets (Secret Manager):
- <env>/DATABASE_URL
- <env>/FIREBASE_PROJECT_ID
- <env>/GCS_MEDIA_BUCKET
- <env>/GCS_REPORTS_BUCKET
- <env>/WHATSAPP_PROVIDER_KEY (or equivalent)
Service Accounts:
- sa-<env>-api
- sa-<env>-worker

## Worker Jobs
Cloud Run Jobs (per env):
- neilsolar-<env>-worker
Jobs executed for:
- report generation
- WhatsApp sending
- retention cleanup

Scheduling:
- retention cleanup nightly
- report generation on-demand (triggered by API) or async queue

## Terraform layout
infra/terraform/
  modules/
  envs/
    dev/
    test/
    staging/
    prod/

One state per env.
Migration to separate GCP projects later is achieved primarily by changing project_id in each env.