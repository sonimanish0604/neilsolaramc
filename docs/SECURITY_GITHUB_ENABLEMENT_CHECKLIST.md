# GitHub Security Enablement Checklist (Manual Settings)

These controls are not fully configured by repo files alone and must be enabled in GitHub repository settings.

## Required Manual Settings
- Enable Dependabot alerts
- Enable Dependabot security updates
- Enable secret scanning
- Enable push protection (if available on your GitHub plan)
- Set branch protection rules for `develop` and `main`:
  - require pull request before merge
  - require status checks to pass before merge
  - include checks:
    - `CI Checks / lint-and-unit`
    - `CI Checks / integration-compose`
    - `Dependency Review / dependency-review`
    - `CodeQL / Analyze (Python)`

## Verification Steps
- Open repository `Security` tab:
  - verify CodeQL alerts view is active
  - verify Dependabot alerts are active
  - verify secret scanning status is enabled
- Open a test PR to `develop`:
  - confirm CI checks run
  - confirm Dependency Review runs
  - confirm CodeQL runs

## Files Added in Repo for Security Automation
- `.github/dependabot.yml`
- `.github/workflows/dependency-review.yml`
- `.github/workflows/codeql.yml`
- `docs/SECURITY_SCAN_STRATEGY.md`

