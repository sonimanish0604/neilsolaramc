# AI Workflow Rules for This Repository

## Purpose

This repository uses AI coding assistants (e.g., Codex, ChatGPT) to help develop a production application.  
This is **not a proof-of-concept project**. All AI-generated work must follow disciplined engineering practices.

These rules ensure:

- safe deployments
- predictable CI/CD behavior
- consistent architecture decisions
- reduced hidden assumptions
- reliable production operations

AI assistants must follow this document before proposing implementation steps.

---

# Core Principle

AI must **work from repository truth**, not generic coding patterns.

Always review:

- README
- Architecture documents
- Runbooks
- Deployment docs
- CI/CD configuration
- Database migration strategy

If documentation is missing, propose documentation before complex automation.

---

# Rule 1 — Treat Every Task as a Dependency Chain

Before writing code or running tests, identify prerequisites.

Typical order of operations:

1. Infrastructure exists
2. Secrets and environment variables exist
3. Database exists
4. Database migrations executed
5. Services start successfully
6. Health checks pass
7. Only then run API or integration tests

Never suggest running business APIs before schema creation or migrations.

---

# Rule 2 — Separate Local, CI, and Cloud Responsibilities

Every workflow must explicitly describe which environment executes each step.

Required breakdown:

## Local Development
Examples:
- developer setup
- linting
- docker compose
- migrations
- unit tests

## Pull Request / CI
Examples:
- lint
- static analysis
- type checking
- unit tests
- build validation

## Post Deploy (Dev Environment)
Examples:
- smoke tests
- migration verification
- service health checks

## Production Deployment
Examples:
- gated deployment
- smoke tests
- rollback readiness

Do not assume steps executed locally are wired into CI/CD.

---

# Rule 3 — Database Migrations Must Be Explicit

Persistence changes must always include migration handling.

AI must specify:

- migration file creation
- when migrations run
- where migrations run
- how migration success is validated
- rollback strategy if migration fails

Deployment plans are incomplete without migration strategy.

---

# Rule 4 — Definition of Done Required

AI tasks must not end with “code written”.

A complete workflow must include:

1. files modified
2. commands to run
3. expected output
4. validation steps
5. failure scenarios
6. rollback options

Major tasks must end with a **verification checklist**.

---

# Rule 5 — Automation Must Be Incremental

Automation must follow a layered approach.

Preferred order:

1. Manual runbook works
2. Repeatable script exists
3. CI validation implemented
4. Cloud deployment automation
5. Post-deploy smoke tests
6. Extended integration automation

AI should avoid recommending large automation pipelines before manual processes are proven.

---

# Rule 6 — Never Assume Cloud Wiring Exists

For cloud environments (GCP, AWS, etc.), verify configuration.

AI must confirm:

- CI trigger exists
- correct branch is monitored
- build configuration path is correct
- container registry exists
- deployment target exists
- runtime service account permissions
- required secrets exist
- environment variables configured

If unknown, ask or flag as assumption.

---

# Rule 7 — Always Provide Verification Steps

AI must define how success is validated.

Examples:

- API health check
- container startup verification
- migration success confirmation
- test execution
- log inspection

Deployment cannot be considered complete without validation.

---

# Recommended Reasoning Levels for AI

AI assistants should choose reasoning effort based on task complexity.

### Medium
Use for:

- small code edits
- endpoint work
- refactoring
- small scripts

### High
Use for:

- CI/CD workflows
- database migrations
- infrastructure changes
- deployment logic
- cross-service integration

### Very High
Use for:

- architecture design
- complex debugging
- multi-system orchestration
- release hardening

---

# Required Output Structure for Complex Tasks

For infrastructure or deployment work, responses should follow this structure:

1. Goal
2. Assumptions
3. Preconditions
4. File changes
5. Commands to run
6. Validation steps
7. Failure scenarios
8. Rollback strategy
9. Manual steps remaining

---

# Example Deployment Order

Typical deployment sequence:

1. Confirm cloud resources exist
2. Confirm secrets and environment variables exist
3. Apply database migrations
4. Build container image
5. Push container to registry
6. Deploy service
7. Execute health check
8. Run smoke tests
9. Verify logs
10. Announce deployment success

---

# Instruction for AI Assistants

When contributing to this repository:

- Follow this document strictly
- Avoid hidden assumptions
- Validate dependencies
- Prefer explicit instructions over implicit behavior
- Prioritize reliability over speed

If uncertain about infrastructure or configuration, request clarification before proceeding.