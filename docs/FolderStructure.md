all-solar-amc-saas/
  README.md
  .gitignore
  LICENSE
  Makefile

  docs/
    ARCHITECTURE.md
    API_CONTRACT.md
    DATA_MODEL.md
    DEPLOYMENT.md
    SECURITY.md
    RUNBOOK.md
    ADR/
      0001-tech-stack.md
      0002-tenant-isolation.md
      0003-whatsapp-approval-link.md
      0004-storage-gcs-not-db.md

  infra/
    terraform/
      modules/
        cloudrun_service/
        cloudrun_job/
        cloudsql_postgres/
        gcs_bucket/
        secret_manager/
        iam/
      envs/
        dev/
          main.tf
          variables.tf
          outputs.tf
          terraform.tfvars.example
        test/
        staging/
        prod/

  backend/
    pyproject.toml
    alembic.ini
    alembic/
      versions/
    app/
      main.py
      core/
        config.py
        logging.py
        security.py          # Firebase JWT verification, RBAC helpers
        tenancy.py           # tenant_id extraction + enforcement
      db/
        session.py
        models/
          tenant.py
          user.py
          customer.py
          site.py
          checklist.py
          workorder.py
          audit.py
        migrations/
      api/
        routes/
          health.py
          auth.py
          tenants.py
          users.py
          customers.py
          sites.py
          workorders.py
          approvals.py
          reports.py
      services/
        report_generator.py  # HTML->PDF
        gcs_storage.py
        whatsapp_sender.py
        retention.py
        audit_logger.py
      schemas/
        tenant.py
        user.py
        customer.py
        site.py
        workorder.py
        report.py
      tests/
        test_workorders.py

  worker/
    app/
      worker_main.py         # entrypoint for Cloud Run Job
      jobs/
        generate_report.py
        send_whatsapp.py
        retention_cleanup.py

  scripts/
    bootstrap_env.sh
    local_db_up.sh
    seed_dev_data.py

  .github/
    workflows/
      ci.yml                 # lint/test
      deploy-dev.yml
      deploy-test.yml
      deploy-staging.yml
      deploy-prod.yml