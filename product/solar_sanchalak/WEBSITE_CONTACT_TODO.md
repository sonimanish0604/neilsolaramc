# Website Contact Form Handoff

## Purpose

This file records the runtime setup needed for the Solar Sanchalak website contact form so future work can continue in a new chat without repeating discovery.

## Current status

- Static landing page exists under `product/solar_sanchalak/site/`
- Production website URL is `https://software.nogginhausenergy.org`
- Production API URL is `https://neilsolar-prod-api-174945359533.asia-south1.run.app`
- Preview website URL is `https://preview.nogginhausenergy.org`
- Website form work has been parked for now
- Public site should remain investor-facing and informational only until form work is resumed intentionally

## Important environment note

Production service is being configured now with the website-contact and Mailgun-related environment variables.

Treat production as already configured for these variables once this setup is complete.

Future follow-up work should focus on the **dev service** unless explicitly asked to revisit prod.

## Production runtime variables

These were intended for `neilsolar-prod-api`:

- `SECRET_PROVIDER=GCP`
- `SECRET_FAIL_OPEN=false`
- `GCP_PROJECT_ID=solar-amc-app-xkoe90`
- `NOTIFICATION_EMAIL_ENABLED=true`
- `NOTIFICATION_EMAIL_PRIMARY_PROVIDER=MAILGUN`
- `NOTIFICATION_MAILGUN_ENABLED=true`
- `NOTIFICATION_MAILGUN_DOMAIN=mail.nogginhausenergy.org`
- `NOTIFICATION_EMAIL_FROM=info@nogginhausenergy.org`
- `NOTIFICATION_MAILGUN_API_KEY_SECRET=notification-mailgun-api-key`
- `WEBSITE_CONTACT_ENABLED=true`
- `WEBSITE_CONTACT_RECIPIENT_EMAIL=info@nogginhausenergy.org`
- `WEBSITE_CONTACT_ALLOWED_ORIGINS=https://software.nogginhausenergy.org`
- `WEBSITE_CONTACT_ACKNOWLEDGEMENT_ENABLED=true`

## Secret Manager note

Mailgun API key secret was created in GCP Secret Manager as:

- `notification-mailgun-api-key`

## Dev service follow-up

Later, mirror the same runtime setup on the dev Cloud Run service.

Expected dev API URL:

- `https://neilsolar-dev-api-174945359533.asia-south1.run.app`

Dev should eventually receive equivalent variables:

- `SECRET_PROVIDER=GCP`
- `SECRET_FAIL_OPEN=false`
- `GCP_PROJECT_ID=solar-amc-app-xkoe90`
- `NOTIFICATION_EMAIL_ENABLED=true`
- `NOTIFICATION_EMAIL_PRIMARY_PROVIDER=MAILGUN`
- `NOTIFICATION_MAILGUN_ENABLED=true`
- `NOTIFICATION_MAILGUN_DOMAIN=mail.nogginhausenergy.org`
- `NOTIFICATION_EMAIL_FROM=info@nogginhausenergy.org`
- `NOTIFICATION_MAILGUN_API_KEY_SECRET=notification-mailgun-api-key`
- `WEBSITE_CONTACT_ENABLED=true`
- `WEBSITE_CONTACT_RECIPIENT_EMAIL=info@nogginhausenergy.org`
- `WEBSITE_CONTACT_ALLOWED_ORIGINS=https://software.nogginhausenergy.org`
- `WEBSITE_CONTACT_ACKNOWLEDGEMENT_ENABLED=true`

## Remaining website tasks

- Keep the live site static and informational for now
- Upload updated static files to DirectAdmin:
  - `index.html`
  - `styles.css`
- Use `preview.nogginhausenergy.org` for dev-facing website experiments before promoting changes to the public site
- Password-protect the preview subdomain in DirectAdmin via `Password Protected Directories`
- Protect this directory for preview:
  - `domains/preview.nogginhausenergy.org/public_html/`
- If form work is resumed later:
  - re-enable frontend form files
  - confirm backend route deployment
  - confirm inquiry email delivery
  - confirm acknowledgment email delivery

## Later spam protection work

- If the form is resumed later, revisit reCAPTCHA with a key type that matches the frontend implementation

## Suggested prompt for future chat

Use `product/solar_sanchalak/WEBSITE_CONTACT_TODO.md` as the handoff file.

Assume:

- prod may already have website-contact env vars configured, but the live website is intentionally email-only for now
- `preview.nogginhausenergy.org` is the right place for protected pre-release website testing
- focus next on product development unless form work is explicitly resumed
