# Phase 1A Local Testing (Docker + API Script)

Use this when validating Phase 1A before merge/deploy.

For Phase 1B validation (notification + approval path), use:
- `docs/PHASE1B_VALIDATION.md`

## Prerequisites
- Docker Engine running on local laptop
- Repo root: `all-solar-amc-SaaS`

## 1) Start local stack manually (optional)
```bash
docker compose --env-file .env.local up -d --build
```

Services:
- API: `http://localhost:8080`
- Postgres: `localhost:5432`
- Adminer (optional profile): `http://localhost:8081`

## 2) Run Phase 1A local API checks
```bash
bash scripts/phase1a_local_api_tests.sh
```

This script will:
- ensure stack is up
- run modular functional scenarios (`UC-1A-*`)
- run happy and rainy path checks
- generate report artifacts

## 3) Review report artifacts
- `reports/phase1a-local/summary.md`
- `reports/phase1a-local/junit.xml`
- `reports/phase1a-local/exit_code.txt` (`0` pass, `1` fail)

## 4) Stop stack when done
```bash
docker compose --env-file .env.local down -v
```
