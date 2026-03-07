# Phase 0 Checklist - Control Plane Foundation

Branch convention:
- `feature/phase0-<short-topic>`

Goal:
- Deliver secure multi-tenant control-plane foundation for MVP.

## 1) Branch + PR hygiene
- [ ] Create feature branch from `develop`
- [ ] Open PR back to `develop` with linked issue
- [ ] Confirm Cloud Build (5 steps) passes on PR branch

## 2) Auth baseline
- [ ] Enforce Firebase JWT on protected routes
- [ ] Keep `AUTH_DISABLED` limited to local/dev only
- [ ] Add negative test for missing/invalid bearer token

## 3) Core control-plane schema
- [ ] Validate tables: `tenants`, `users`, `user_roles`, `audit_log`
- [ ] Ensure required indexes on tenant/user lookup paths
- [ ] Verify Alembic upgrade/downgrade path is clean

## 4) Admin bootstrap endpoints (manual pilot mode)
- [ ] `POST /admin/tenants`
- [ ] `POST /admin/users`
- [ ] `POST /admin/users/{id}/roles`
- [ ] Add conflict handling and input validation

## 5) Tenant isolation and RLS
- [ ] Confirm `tenant_id` exists on all tenant-scoped tables
- [ ] Confirm RLS policies are enabled + forced
- [ ] Confirm request transaction sets `app.tenant_id`
- [ ] Add isolation tests (cross-tenant read/write blocked)

## 6) Audit logging (append-only)
- [ ] Implement `audit_log` write path for sensitive actions
- [ ] Log: actor, tenant, action, entity, metadata, timestamp
- [ ] Prevent update/delete on audit entries

## 7) Health and readiness
- [ ] Keep `/health`
- [ ] Add `/ready` with DB connectivity check
- [ ] Include readiness check in ops runbook

## 8) CI quality gate
- [ ] Ruff lint must fail pipeline on violations
- [ ] Minimal tests for auth + tenant isolation
- [ ] Ensure smoke check remains green after deploy

## 9) Docs and runbook updates
- [ ] Update architecture notes for Phase 0 decisions
- [ ] Add bootstrap runbook for first tenant/user creation
- [ ] Keep `SEC-001` launch gate visible in runbook

## 10) Done criteria (Phase 0 exit)
- [ ] New tenant + users can be bootstrapped via admin APIs
- [ ] Auth and tenant isolation verified by tests
- [ ] Audit logs recorded for admin/bootstrap actions
- [ ] Deploy on `develop` is green end-to-end
