# Branching and Release Strategy – NEIL Solar AMC SaaS

## 1. Branch Model

Long-lived branches:

- main → Production
- staging → Pre-production
- test → QA validation
- develop → Active development

Short-lived branches:

- feature/<feature-name>
- doc/<if-adding-only-documents>
- fix/<adding fixes>
- 

Example:
feature/phase0-control-plane
feature/workorder-inverters
feature/logo-upload

---

## 2. Environment Mapping

| Branch     | Environment | Cloud Run Service         |
|------------|------------|----------------------------|
| develop    | dev        | neilsolar-dev-api          |
| test       | test       | neilsolar-test-api         |
| staging    | staging    | neilsolar-staging-api      |
| main       | production | neilsolar-prod-api         |

Cloud Run services are configured for continuous deployment from their respective branches.

---

## 3. Development Workflow

### Step 1 – Create Feature Branch

Branch from develop:

git checkout develop
git pull
git checkout -b feature/<feature-name>

---

### Step 2 – Local Development

- Implement feature
- Run locally:
  uvicorn app.main:app --reload
- Apply migrations locally or against dev DB:
  alembic upgrade head
- Validate endpoints

---

### Step 3 – Push Feature Branch

git push -u origin feature/<feature-name>

---

### Step 4 – Pull Request to develop

- Open PR: feature → develop
- Review changes
- Merge PR

After merge:
- GitHub updates develop branch
- Cloud Build (GCP) builds Docker image
- Cloud Run dev service redeploys automatically

---

## 4. Promotion Flow

### develop → test

- Open PR
- Merge
- Cloud Run test service auto-deploys
- Run QA validation

### test → staging

- Open PR
- Merge
- Cloud Run staging auto-deploys
- Run pre-production validation

### staging → main

- Open PR
- Merge
- Cloud Run production auto-deploys
- Run smoke tests

---

## 5. Database Migrations

Cloud Run does not automatically run migrations.

Before validating any environment:
- Run alembic upgrade head against that environment's DB.

Future improvement:
- Add migration step inside Cloud Build pipeline.

---

## 6. Ephemeral Environments

Test branch may remain persistent in early stage.

Infrastructure tear-down automation is optional and can be introduced later using Terraform.

Early stage recommendation:
- Keep dev, staging, production persistent.
- Avoid complex ephemeral infra until user base grows.

---

## 7. Rules

- Never commit directly to main.
- All changes must go through feature branches.
- All production releases must pass staging validation.
- RLS tenant isolation must be verified in test before promotion.