# Secret Management (Local Vault + GCP Secret Manager)

This project supports three secret sources:

- `SECRET_PROVIDER=ENV` (default): use inline env values.
- `SECRET_PROVIDER=VAULT`: fetch from HashiCorp Vault.
- `SECRET_PROVIDER=GCP`: fetch from Google Secret Manager.

If secret fetch fails:
- `SECRET_FAIL_OPEN=true` (default): fallback to inline env value.
- `SECRET_FAIL_OPEN=false`: fail fast.

## Supported secret refs

- `NOTIFICATION_MAILGUN_API_KEY_SECRET`
- `NOTIFICATION_TWILIO_SENDGRID_API_KEY_SECRET`
- `TWILIO_AUTH_TOKEN_SECRET`
- `NOTIFICATION_EMAIL_SMTP_PASSWORD_SECRET`

Inline env variables still work:
- `NOTIFICATION_MAILGUN_API_KEY`
- `NOTIFICATION_TWILIO_SENDGRID_API_KEY`
- `TWILIO_AUTH_TOKEN`
- `NOTIFICATION_EMAIL_SMTP_PASSWORD`

## Local Vault (laptop) quick start

1. Start Vault dev server:

```bash
docker run --cap-add=IPC_LOCK --rm \
  -e VAULT_DEV_ROOT_TOKEN_ID=root \
  -p 8200:8200 \
  hashicorp/vault:1.16
```

2. Seed notification secrets:

```bash
bash scripts/local/vault_seed_notification_secrets.sh
```

3. Set env in `.env.local`:

```bash
SECRET_PROVIDER=VAULT
SECRET_FAIL_OPEN=true
VAULT_ADDR=http://host.docker.internal:8200
VAULT_TOKEN=root
VAULT_MOUNT=secret
VAULT_KV_VERSION=2

NOTIFICATION_MAILGUN_API_KEY_SECRET=neilsolar/local/notification#mailgun_api_key
NOTIFICATION_TWILIO_SENDGRID_API_KEY_SECRET=neilsolar/local/notification#sendgrid_api_key
TWILIO_AUTH_TOKEN_SECRET=neilsolar/local/twilio#auth_token
NOTIFICATION_EMAIL_SMTP_PASSWORD_SECRET=neilsolar/local/smtp#password
```

Vault secret ref format is:

```text
<path>#<field>
```

Example:

```text
neilsolar/local/notification#mailgun_api_key
```

## GCP Secret Manager setup

1. Create secrets (one-time):

```bash
gcloud secrets create notification-mailgun-api-key --replication-policy="automatic"
gcloud secrets versions add notification-mailgun-api-key --data-file=-
```

2. Grant Cloud Run service account access:

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<SERVICE_ACCOUNT_EMAIL>" \
  --role="roles/secretmanager.secretAccessor"
```

3. Set env in runtime:

```bash
SECRET_PROVIDER=GCP
SECRET_FAIL_OPEN=false
GCP_PROJECT_ID=<PROJECT_ID>
NOTIFICATION_MAILGUN_API_KEY_SECRET=notification-mailgun-api-key
```

You can also use full resource names:

```text
projects/<PROJECT_ID>/secrets/<SECRET_NAME>/versions/latest
```
