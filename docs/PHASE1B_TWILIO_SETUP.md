# Phase 1B Twilio Setup

Use this when enabling WhatsApp delivery in `develop`.

For full Phase 1B validation flow (local + cloud), see:
- `docs/PHASE1B_VALIDATION.md`

## 1. Fill runtime env from template

Template file:
- `backend/.env.phase1b.template`

Copy these values into your runtime env file (for example `backend/.env.local`):
- `APPROVAL_BASE_URL`
- `APPROVAL_TOKEN_TTL_HOURS` (must stay `72`)
- `TWILIO_ENABLED`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM` (sandbox sender, usually `whatsapp:+14155238886`)
- `TWILIO_REQUEST_TIMEOUT_SECONDS`
- `PDF_BRAND_LABEL`

## 2. Required values from Twilio Console

- Account SID
- Auth Token
- WhatsApp Sandbox sender number
- Approved recipient numbers joined to sandbox

## 3. Safe rollout order

1. Keep `TWILIO_ENABLED=false` and validate API flow locally.
2. Set sandbox credentials and flip `TWILIO_ENABLED=true` on `develop`.
3. Run functional scenario `uc_1b_001_approval_token_flow` with a fresh approval token.
4. Verify delivery status and message SID in API response.
