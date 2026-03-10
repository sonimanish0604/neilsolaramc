# Notification Engine Design (Canonical, Phase B)

Canonical source for this design:
- `/updated_ASCII_notif_engine.txt`
- `/updated_component_notif_engine.puml`
- `/updated_sequence_diagram.puml`

## 1. Scope

Phase B canonical flow is email-first and provider-agnostic:
- in scope: `EMAIL` notification queueing, routing, delivery, retry/failover, attempts logging
- out of scope in this document: `WHATSAPP`, `SMS`

## 2. Canonical Architecture

1. `Business Services`
- Publish business events (`work_order.completed`, `work_order.submitted_for_approval`, etc.).

2. `Notification Orchestrator`
- Resolves template.
- Resolves recipients.
- Creates neutral job record.

3. `notification_jobs`
- Provider-agnostic queue.
- Initial status: `queued`.
- Logical name used in architecture diagrams.
- Physical storage lifecycle uses active/history tables from `docs/NOTIFICATION_RETENTION.md`.

4. `Email Worker`
- Fetches queued jobs.
- Selects provider using routing rules.
- Sends email.
- Applies retry/failover policy.

5. `Provider Router`
- Primary provider: `Mailgun`.
- Secondary provider: `SendGrid` (or another configured email adapter).

6. `notification_attempts`
- Provider-specific attempt records.
- Tracks `sent`, `failed`, retry path, and dead-letter transitions.
- Logical name used in architecture diagrams.
- Physical storage lifecycle uses active/history tables from `docs/NOTIFICATION_RETENTION.md`.

## 3. Recipient Source Rule

Recipient resolution is DB-driven, not env-driven:
- email recipient source: `sites.site_supervisor_email`

## 4. Runtime and Operations

Containerized runtime:
- `backend/Dockerfile.notification-engine`
- `python -m app.notification_engine.run_service`

One-shot operational commands:
- `bash scripts/notification/run_once_notification_role.sh WORKER_EMAIL`
- `bash scripts/notification/run_notification_maintenance_once.sh archive`
- `bash scripts/notification/run_notification_maintenance_once.sh purge`

## 5. Related Canonical Docs

- Component diagram: `docs/notif-engine-flow.puml`
- Sequence diagram: `docs/notif-engine-sequence.puml`
- Event catalog: `docs/NOTIFICATION_EVENTS.md`
- Retention and purge lifecycle: `docs/NOTIFICATION_RETENTION.md`
- Secret management: `docs/SECRET_MANAGEMENT.md`
