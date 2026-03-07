# Security Scan Strategy for Git Workflow (develop / main)

## Objective

Build security discipline into the delivery process early, instead of adding it later as a separate cleanup phase.

This strategy adds security checks at the right layers:

- **GitHub / PR stage** for source-code and dependency risks
- **GCP / build stage** for container-image risks
- **Later phase** for lightweight DAST against deployed dev environment

GitHub’s code scanning is designed to find vulnerabilities and coding errors in repository code, Dependabot alerts and dependency review focus on vulnerable dependencies and risky dependency changes, and Google Artifact Analysis scans container images stored in Artifact Registry for vulnerabilities. :contentReference[oaicite:0]{index=0}

---

## High-level policy

### In GitHub (before merge)
Run these checks in PRs targeting `develop` and `main`:

1. **SAST / code scanning**
   - Use GitHub code scanning / CodeQL
   - Purpose: detect code-level vulnerabilities and coding mistakes before merge

2. **Dependabot alerts**
   - Enable repository dependency vulnerability alerts

3. **Dependabot security updates**
   - Allow automated PRs to upgrade vulnerable packages

4. **Dependency review**
   - Run on pull requests to detect risky dependency additions/changes before merge

5. **Secret scanning**
   - Enable secret scanning
   - If available on the plan, also enable push protection

GitHub documents these capabilities as repo-level code scanning, dependency review, Dependabot alerts/security updates, and secret scanning/push protection. :contentReference[oaicite:1]{index=1}

### In GCP / Cloud Build (after build)
Run these checks after building the image:

1. **Container image vulnerability scanning**
   - Scan images in Artifact Registry using Artifact Analysis / Container Scanning

2. **Optional severity gate**
   - Fail the build or block promotion if vulnerability severity exceeds policy threshold

Google documents automatic and on-demand container scanning for images in Artifact Registry through Artifact Analysis. :contentReference[oaicite:2]{index=2}

### Later (not day 1)
3. **DAST**
   - Add lightweight DAST against deployed `dev` service once APIs and auth flows stabilize
   - This should come after the above controls are in place

---

## Branch model

We are using only:

- `develop`
- `main`

### develop branch
- active integration branch
- PRs into `develop` run source/dependency/security checks
- merge to `develop` triggers Cloud Build
- Cloud Build builds image, pushes image, scans image, deploys dev service, runs smoke checks

### main branch
- production branch
- PRs into `main` run same source/dependency/security checks
- merge to `main` triggers production build/deploy flow
- production should use minimal, safe post-deploy smoke checks

---

## What should be blocking vs non-blocking

### Blocking in PRs
These should block merge if they fail:

- lint
- unit/integration tests
- SAST / code scanning
- dependency review
- secret scanning findings for committed secrets (depending on repo policy)

### Non-blocking initially in PRs
These can start as alerts-only:

- Dependabot version updates
- lower-severity code scanning findings that need triage

### Blocking after image build (recommended)
These can be made blocking once pipeline is stable:

- critical image vulnerabilities
- high image vulnerabilities in runtime packages

### Non-blocking initially after image build
These can begin as informational:

- medium/low image vulnerabilities
- image secret findings pending triage

Artifact Analysis supports automatic and on-demand scanning; GitHub surfaces code and secret alerts in the repository security experience. :contentReference[oaicite:3]{index=3}

---

## Recommended implementation order

### Phase 1: add now
Implement immediately after current feature work, or include now if effort is manageable:

1. **Dependabot alerts**
2. **Dependabot security updates**
3. **Dependency review on PRs**
4. **GitHub code scanning / CodeQL**
5. **Secret scanning**
6. **Artifact Registry vulnerability scanning**

This gives strong value early without making the pipeline too heavy. GitHub supports Dependabot alerts/security updates and dependency review for dependency risk management, while Artifact Analysis covers image-level vulnerabilities. :contentReference[oaicite:4]{index=4}

### Phase 2: add after core APIs stabilize
1. severity thresholds for image scan gates
2. better triage workflow
3. secret scanning custom patterns if needed
4. optional SARIF or richer reporting

GitHub secret scanning supports default detection and can be expanded with non-provider and custom patterns where available. :contentReference[oaicite:5]{index=5}

### Phase 3: add after dev environment is stable
1. lightweight DAST against dev deployment
2. only against non-production environment
3. focus on auth, exposed APIs, headers, and obvious web-risk checks

---

## Why we are doing this

### Benefits

1. **Catch insecure code earlier**
   - SAST/code scanning finds code-level issues before merge

2. **Reduce dependency risk**
   - Dependabot alerts identify known vulnerable dependencies
   - dependency review prevents risky changes from being introduced casually

3. **Reduce image/base package risk**
   - Artifact Analysis scans built container images, including OS packages and dependencies

4. **Improve audit and hardening posture**
   - This creates evidence that security checks are part of delivery, not an afterthought

GitHub and Google both position these features as part of secure software supply chain and vulnerability detection workflows. :contentReference[oaicite:6]{index=6}

---

## Required implementation intent for Codex

Please implement or verify the following:

### GitHub / PR stage
- Enable Dependabot alerts
- Add `dependabot.yml` for security/version updates
- Add dependency review action to PR workflow
- Enable GitHub code scanning / CodeQL
- Enable secret scanning
- If available, enable push protection
- Ensure PR security checks run on both:
  - PR to `develop`
  - PR to `main`

### Cloud / build stage
- Ensure Artifact Registry image scanning is enabled
- After image push, surface vulnerability results in build logs or deployment decision flow
- Add initial policy:
  - fail or warn on critical vulnerabilities
  - warn on high until thresholds are tuned

### Governance / behavior
- Keep findings visible in CI output
- Start simple: pass/fail + alert summary is enough
- Do not block delivery on every low-severity issue immediately
- Focus on:
  - critical secrets
  - obvious code vulnerabilities
  - vulnerable dependencies
  - critical image vulnerabilities

---

## Suggested practical gating policy (starter)

### PR to develop
**Blocking**
- lint/tests
- dependency review
- SAST/code scanning if severe findings exist
- secret leak findings

**Advisory**
- general Dependabot alerts
- lower-severity CodeQL findings

### Merge to develop -> build/deploy
**Blocking**
- build succeeds
- image push succeeds
- no critical image vulnerabilities (once stable)
- smoke deploy checks pass

**Advisory initially**
- high/medium image vulnerabilities

### PR to main / merge to main
Same pattern, but stricter:
- no secret findings
- no critical image findings
- no unresolved severe code-scanning findings

---

## Things we are explicitly NOT doing yet

- full enterprise DAST program
- complex security orchestration
- heavy compliance evidence automation
- blocking on every medium/low severity issue immediately

We want useful, maintainable security controls first.

---

## Deliverables Codex can create

1. GitHub workflow updates for:
   - code scanning
   - dependency review
   - security checks in PRs

2. `dependabot.yml`

3. Documentation update:
   - security checks by stage
   - blocking vs advisory findings

4. Cloud Build integration notes or scripts for:
   - Artifact Registry vulnerability scanning visibility
   - optional future severity gates

---

## Short version

Security checks should be split by layer:

### GitHub / PR
- SAST / CodeQL
- Dependabot alerts
- Dependabot security updates
- Dependency review
- Secret scanning

### GCP / Build
- Artifact Registry / Artifact Analysis image vulnerability scanning

### Later
- DAST against dev deployment

This gives early code/dependency protection before merge and image protection after build, without overloading the current pipeline.
