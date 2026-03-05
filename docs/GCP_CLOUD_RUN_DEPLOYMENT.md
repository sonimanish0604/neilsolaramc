# GCP Cloud Run: Repo-connected Deployments (Cloud Build → Cloud Run)

This repo deploys the API to Google Cloud Run using Cloud Build.
It is equivalent to the "Render connected to Git repo" workflow:
- Git repo change -> build -> deploy -> hosted API.

## 0) Variables to standardize

Set these values once for your environment:

- PROJECT_ID=solar-amc-app-xkoe90
- REGION=asia-south1
- AR_REPO=neilsolar-containers
- PROJECT_NUMBER=174945359533

Service naming convention (recommended):
- dev:     neilsolar-dev-api
- test:    neilsolar-test-api
- staging: neilsolar-staging-api
- prod:    neilsolar-prod-api

Image naming convention:
- IMAGE=amc-api
- TAG=<git-sha> or <branch-name> (Cloud Build can set this)

Artifact Registry image path:
asia-south1-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE}:${TAG}

---

## 1) Required GCP artifacts

### 1.1 Artifact Registry repository
- Ensure Artifact Registry repo exists in REGION:
  ${AR_REPO}

### 1.2 Cloud SQL instance (if API uses Postgres)
- Instance: neilsolar-amc
- API runtime SA needs roles/cloudsql.client
- Cloud Run deploy must attach the instance connection name

### 1.3 Storage buckets (current)
- neilsolar-dev-media
- neilsolar-dev-reports

### 1.4 Service Accounts (Dev-only for now)
Create these SAs in PROJECT_ID:

1) CI/CD deployer (dev)
- sa-neilsolar-cicd-dev
Roles:
- roles/artifactregistry.writer
- roles/run.admin
- roles/iam.serviceAccountUser on the runtime SA below

2) Runtime API (dev)
- sa-neilsolar-api-dev
Roles:
- roles/cloudsql.client
- roles/secretmanager.secretAccessor
Bucket-level:
- roles/storage.objectAdmin on gs://neilsolar-dev-media
- roles/storage.objectAdmin on gs://neilsolar-dev-reports

(Optional)
3) Auditor/Inspector
- sa-neilsolar-auditor
Roles:
- roles/viewer
- roles/logging.viewer
- roles/monitoring.viewer

---

## 2) Create a NEW Cloud Run service (first-time)

You can create it once (even with a placeholder image), then CI/CD updates it.

Recommended:
SERVICE=neilsolar-dev-api
RUNTIME_SA=sa-neilsolar-api-dev@${PROJECT_ID}.iam.gserviceaccount.com

Attach secrets as env vars (Secret Manager), and attach Cloud SQL if needed.

You can do this either:
- via Console UI (Cloud Run → Create service → from container image), OR
- via CLI (gcloud run deploy)

Important settings:
- Region: ${REGION}
- Authentication: decide:
  - Public (unauthenticated) for now, OR
  - Private (authenticated) if you want only clients with auth tokens
- Runtime service account: ${RUNTIME_SA}

---

## 3) Connect the repo: Cloud Build Trigger

Create a Cloud Build trigger:
- Repository: this GitHub repo
- Event: push to branch "develop" (for dev)
- Build config: cloudbuild.yaml in repo

This makes:
develop branch -> Cloud Build -> deploy to Cloud Run service (dev)

Later, you can add more triggers:
- test branch -> deploy to neilsolar-test-api
- staging branch -> deploy to neilsolar-staging-api
- main branch -> deploy to neilsolar-prod-api

---

## 4) cloudbuild.yaml (template)

Place this in repo root as cloudbuild.yaml, or adjust trigger to point to it.
This template:
- builds image
- pushes to Artifact Registry
- deploys to Cloud Run

NOTE:
- Replace SERVICE name per environment trigger (or use substitutions).

```yaml
substitutions:
  _REGION: "asia-south1"
  _AR_REPO: "neilsolar-containers"
  _IMAGE: "amc-api"
  _SERVICE: "neilsolar-dev-api"
  _RUNTIME_SA: "sa-neilsolar-api-dev@solar-amc-app-xkoe90.iam.gserviceaccount.com"

steps:
  - name: "gcr.io/cloud-builders/docker"
    args:
      [
        "build",
        "-t",
        "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/${_IMAGE}:$SHORT_SHA",
        "."
      ]

  - name: "gcr.io/cloud-builders/docker"
    args:
      [
        "push",
        "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/${_IMAGE}:$SHORT_SHA"
      ]

  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: "gcloud"
    args:
      [
        "run", "deploy", "${_SERVICE}",
        "--image", "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/${_IMAGE}:$SHORT_SHA",
        "--region", "${_REGION}",
        "--platform", "managed",
        "--service-account", "${_RUNTIME_SA}",
        "--allow-unauthenticated"
      ]

images:
  - "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/${_IMAGE}:$SHORT_SHA"