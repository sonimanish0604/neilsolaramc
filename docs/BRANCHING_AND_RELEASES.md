# Branching and Release Strategy – Current MVP

## Active Branch Model

Long-lived branches:
- `develop` -> Dev environment
- `main` -> Production environment

Short-lived branches:
- `feature/<feature-name>`
- `fix/<fix-name>`
- `doc/<doc-change-name>`

## Promotion Flow
- `feature/*` -> `develop`
- `develop` -> `main`

Rules:
- No direct commits to `main`
- All changes through PRs
- CI/CD and post-deploy checks must pass before promotion

## Environment Mapping

| Branch | Environment | Cloud Run Service |
|---|---|---|
| develop | dev | neilsolar-dev-api |
| main | prod | neilsolar-prod-api |

## Delivery Workflow
1. Create branch from `develop`
2. Implement and validate locally
3. Push branch and open PR to `develop`
4. Merge to `develop` after checks
5. Promote to `main` through PR after validation

## Database Migrations
- Migrations are executed in Cloud Build before service deploy.
- Local/dev checks should still run `alembic upgrade head` before API validation.

## Future Expansion (Deferred)
- Additional long-lived branches/environments (`test`, `staging`) are deferred.
- Re-introduce only when release governance needs that complexity.
