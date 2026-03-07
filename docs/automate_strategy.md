# Automation Strategy V1 (Checklist)

Scope:
- GitHub branches: `develop`, `main`
- Local testing: Docker Compose (`api + postgres`, optional `adminer`)
- Cloud deployment: Cloud Build -> Artifact Registry -> Cloud Run

## Local Quick Start (One Command)

- [ ] Copy env template: `cp .env.local.example .env.local`
- [ ] Start local stack: `docker compose --env-file .env.local up --build`
- [ ] Verify API health: `curl http://localhost:8080/health`
- [ ] Optional Adminer: `docker compose --env-file .env.local --profile adminer up --build`
- [ ] Stop stack: `docker compose --env-file .env.local down`

## A) PR to `develop` (Before Merge)

### Required checks
- [ ] Ruff lint passes
- [ ] Unit tests pass (`pytest`)
- [ ] Integration/API tests pass on local stack pattern:
- [ ] Happy paths:
- [ ] Create tenant
- [ ] Create user
- [ ] Assign user role
- [ ] Rainy paths:
- [ ] Duplicate tenant/user returns `409`
- [ ] Invalid role returns `400`
- [ ] Unauthorized request returns `401`
- [ ] User not found returns `404`

### Output to keep
- [ ] Pytest console output
- [ ] JUnit XML (if enabled)
- [ ] CI summary with pass/fail counts and failed test names

## B) Merge to `develop` (Post-Merge Deployment to DEV)

### Cloud Build pipeline
- [ ] Build image
- [ ] Push image
- [ ] Deploy to Cloud Run dev service (`neilsolar-dev-api`)
- [ ] Inject secrets from Secret Manager
- [ ] Connect to Cloud SQL dev
- [ ] Run post-deploy smoke checks

### Smoke checks (DEV)
- [ ] `GET /health` returns `200`
- [ ] Optional: `GET /openapi.json` returns `200`
- [ ] Optional safe DB-backed API read/create-read check (dev only)

## C) Promote `develop` -> `main`

### Pre-merge checks on PR to `main`
- [ ] Same quality gates as PR to `develop` (lint + unit + integration)
- [ ] Confirm `develop` environment is stable

### Post-merge deployment to PROD
- [ ] Build image
- [ ] Push image
- [ ] Deploy to Cloud Run prod service (`neilsolar-prod-api`)
- [ ] Inject prod secrets
- [ ] Connect to Cloud SQL prod
- [ ] Run minimal smoke checks (`/health`)

## D) Reporting and Speed Guardrails

- [ ] Keep reports minimal while tests are evolving
- [ ] Prefer simple artifacts first:
- [ ] Pytest output
- [ ] Optional JUnit XML
- [ ] CI job summary
- [ ] Add coverage/HTML reports only after tests stabilize

## E) Security and Reliability Guardrails

- [ ] No hardcoded DB credentials in code
- [ ] Use Secret Manager for cloud env vars
- [ ] Keep local and cloud DB infra separate
- [ ] Track and close `SEC-001` before production launch

## F) Definition of Done (Automation V1)

- [ ] PR to `develop` is blocked unless required checks pass
- [ ] Merge to `develop` auto-deploys dev successfully
- [ ] PR to `main` is blocked unless required checks pass
- [ ] Merge to `main` auto-deploys prod successfully
- [ ] Smoke checks are green in both dev and prod
