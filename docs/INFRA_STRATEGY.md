# Infrastructure Strategy – NEIL Solar AMC SaaS

## 1. Philosophy

NEIL Solar AMC SaaS is built using a **stage-appropriate infrastructure strategy**.

We prioritize:
- Speed of delivery
- Low operational overhead
- Security-by-design (RLS, JWT auth)
- Scalable container deployment
- Clear upgrade path toward enterprise-grade infrastructure

We intentionally avoid premature infrastructure complexity.

---

## 2. Current Architecture Model (Stage 1)

### Deployment Model
- GitHub for version control
- Branch-based release flow
- Cloud Build for container builds
- Cloud Run for runtime
- Cloud SQL (Postgres) for database
- Google Cloud Storage for media + PDFs

### Environment Mapping

| Branch   | Environment | Cloud Run Service |
|----------|------------|------------------|
| develop  | dev        | neilsolar-dev-api |
| test     | test       | neilsolar-test-api |
| staging  | staging    | neilsolar-staging-api |
| main     | production | neilsolar-prod-api |

### Why Cloud Run (Container-first)
- Fully managed
- No VM management
- Auto-scaling (including scale-to-zero)
- Simple deploy model
- Minimal DevOps overhead
- Suitable for early-stage SaaS

---

## 3. Why We Are NOT Using Infrastructure-First (Terraform-driven Ephemeral Infra) Yet

We are intentionally not using:
- Full Terraform provisioning per branch
- Ephemeral environment spin-up/tear-down
- Complex VPC topologies
- Preview environments per PR

### Reasoning

1. Solo developer
2. Early-stage product validation
3. Low tenant count (< 20 expected initially)
4. Cloud Run removes most infrastructure burden
5. Database (Cloud SQL) is the primary cost anchor
6. Over-automation at this stage slows iteration

Infrastructure-first automation adds:
- Pipeline maintenance overhead
- Terraform drift management
- Increased cognitive complexity
- Reduced feature velocity

At this stage, speed > infra perfection.

---

## 4. Security Model (Current Stage)

Even without infrastructure-first automation, we maintain:

- Firebase JWT verification
- Postgres Row Level Security (RLS)
- Admin vs App DB roles (BYPASSRLS separation)
- Strict tenant isolation at database level
- Branch-based release discipline
- Staging validation before production merge

Tenant isolation is enforced at the database kernel level.

---

## 5. When We Will Move Toward Infrastructure-First

We will introduce Terraform-driven infrastructure when ANY 2+ of the following are true:

- 50+ tenants onboarded
- 3+ active engineers
- Paying customers demand compliance evidence
- SOC2 / ISO 27001 preparation begins
- Regressions become frequent
- Multi-region deployment required
- Dedicated VPC / private networking required
- Cost of persistent test environments becomes significant

At that stage we may introduce:

- Full Terraform management of:
  - Cloud Run
  - Cloud SQL
  - GCS
  - IAM
- Ephemeral test environments per PR
- Migration execution inside CI
- Integration tests in isolated infra
- DAST pipeline
- Audit trail automation

---

## 6. Upgrade Path (Future State)

Stage 2:
- Add GitHub Actions for:
  - lint
  - unit tests
  - dependency scan
- Add integration tests hitting dev Cloud Run

Stage 3:
- Terraform-managed infra
- Automated migrations in pipeline
- Preview environments
- Infrastructure drift detection

Stage 4:
- Compliance-ready deployment model
- Secret rotation automation
- Backup + DR policy automation
- Centralized logging + monitoring

---

## 7. Guiding Principle

Infrastructure must:
- Support the product
- Not slow down product iteration
- Not consume disproportionate engineering time
- Remain upgradeable

We choose the simplest scalable option until complexity is justified.

---

## 8. Summary

Current Strategy:
- Container-first
- Cloud Run managed
- Minimal DevOps overhead
- Strong database isolation
- Structured branch promotion model

Future Strategy:
- Terraform + CI-driven infra
- Compliance-ready
- Multi-engineer safe

We evolve infrastructure as the business grows.