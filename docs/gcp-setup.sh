#!/usr/bin/env bash
set -euo pipefail

# gcp-setup.sh
# Create runtime and (optional) CI service accounts and grant IAM roles
# Uses exact names from docs/GCP_CLOUD_RUN_DEPLOYMENT.md

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 PROJECT_ID [PROJECT_NUMBER]"
  exit 2
fi

PROJECT_ID="$1"
PROJECT_NUMBER="${2:-}" # optional numeric project number
REGION="asia-south1"
AR_REPO="neilsolar-containers"

# Derived names from docs
RUNTIME_SA="sa-neilsolar-api-dev@${PROJECT_ID}.iam.gserviceaccount.com"
CI_DEFAULT_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "Project: ${PROJECT_ID}"
if [ -z "${PROJECT_NUMBER}" ]; then
  echo "WARNING: PROJECT_NUMBER not provided; using default Cloud Build SA will be skipped until you supply it."
fi

# Create runtime SA
echo "Creating runtime service account: ${RUNTIME_SA}"
gcloud iam service-accounts create sa-neilsolar-api-dev \
  --project="${PROJECT_ID}" \
  --description="Cloud Run runtime SA for neilsolaramc (dev)" \
  --display-name="sa-neilsolar-api-dev"

echo "Granting runtime roles to ${RUNTIME_SA}"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"

echo "For storage permissions, consider granting bucket-specific roles. Example below (not executed):"
echo "  gsutil iam ch serviceAccount:${RUNTIME_SA}:roles/storage.objectAdmin gs://neilsolar-dev-media"
echo "  gsutil iam ch serviceAccount:${RUNTIME_SA}:roles/storage.objectAdmin gs://neilsolar-dev-reports"

if [ -n "${PROJECT_NUMBER}" ]; then
  echo "Configuring Cloud Build default SA: ${CI_DEFAULT_SA}"

  echo "Granting build/push/deploy roles to Cloud Build SA"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CI_DEFAULT_SA}" \
    --role="roles/cloudbuild.builds.builder"

  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CI_DEFAULT_SA}" \
    --role="roles/artifactregistry.writer"

  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CI_DEFAULT_SA}" \
    --role="roles/run.admin"

  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CI_DEFAULT_SA}" \
    --role="roles/secretmanager.secretAccessor"

  echo "Allow Cloud Build SA to impersonate runtime SA"
  gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA}" \
    --member="serviceAccount:${CI_DEFAULT_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --project="${PROJECT_ID}"
else
  echo "Skipping Cloud Build SA bindings — supply PROJECT_NUMBER as second arg to enable them."
fi

echo "Optional: create dedicated CI deployer SA (sa-neilsolar-cicd-dev)"
echo "Run these commands if you want a dedicated CI SA instead of using default Cloud Build SA:"
echo "  gcloud iam service-accounts create sa-neilsolar-cicd-dev --project=${PROJECT_ID} --description='CI/CD deployer (dev)' --display-name='sa-neilsolar-cicd-dev'"
echo "  gcloud projects add-iam-policy-binding ${PROJECT_ID} --member=serviceAccount:sa-neilsolar-cicd-dev@${PROJECT_ID}.iam.gserviceaccount.com --role=roles/artifactregistry.writer"
echo "  gcloud projects add-iam-policy-binding ${PROJECT_ID} --member=serviceAccount:sa-neilsolar-cicd-dev@${PROJECT_ID}.iam.gserviceaccount.com --role=roles/run.admin"
echo "  gcloud iam service-accounts add-iam-policy-binding sa-neilsolar-api-dev@${PROJECT_ID}.iam.gserviceaccount.com --member=serviceAccount:sa-neilsolar-cicd-dev@${PROJECT_ID}.iam.gserviceaccount.com --role=roles/iam.serviceAccountUser --project=${PROJECT_ID}"

echo "Done. Review bindings with: gcloud projects get-iam-policy ${PROJECT_ID}"
