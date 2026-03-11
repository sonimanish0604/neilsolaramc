# Folder Structure (Current MVP Snapshot)

This is a practical snapshot of current repository layout (not a strict future-state blueprint).

```text
all-solar-amc-saas/
  cloudbuild.yaml
  docker-compose.yml
  scripts/
    phase1a_local_api_tests.sh
    phase1c_local_api_tests.sh
    phase1c_post_deploy_tests.sh
    post_deploy_cloud_tests.sh
    functional/

  backend/
    alembic/
      versions/
    app/
      main.py
      api/routes/
        admin.py
        application.py
        approvals.py
        health.py
        logos.py
        workorders.py
      core/
        config.py
        correlation.py
        logging.py
        security.py
        tenancy.py
      db/
        session.py
        models/
          audit_log.py
          base.py
          checklist.py
          site.py
          tenant.py
          user.py
          workorder.py
      schemas/
        admin.py
        application.py
        approvals.py
        logos.py
        workorders.py
      services/
        approval_tokens.py
        email_sender.py
        report_generator.py
        report_jobs.py
        whatsapp_sender.py
    tests/

  docs/
    README.md
    ARCHITECTURE.md
    API_CONTRACT.md
    DATA_MODEL.md
    RUNBOOK.md
    TEST_STRATEGY_PHASE1.md
    TEST_CASES_PHASE1.md
    PHASE1_USE_CASE_TESTS.md
    PHASE1B_CLOSURE_NOTE.md
    PHASE1C_ACCOMPLISHMENTS_AND_NEXT_STEPS.md
```

## Notes
- Active long-lived branches are `develop` and `main`.
- `test` and `staging` are deferred for future expansion.
- Notification/report resiliency and correlation tracking are implemented in service and API layers listed above.
