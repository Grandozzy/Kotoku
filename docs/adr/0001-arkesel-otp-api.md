# ADR-0001: Replace local OTP management with Arkesel OTP API

**Date:** 2026-07-18

## Status

Accepted

## Context

Kotoku sends OTPs for login and consent verification via SMS. The current stack uses Africa Talking via `SmsGateway` for delivery, with custom local OTP management: generation, hashing, DB storage in `OTPRequest`, expiry caching, rate limiting, lockout logic, and hash comparison on verify.

Africa Talking's deliverability in Ghana has been poor — messages delayed or lost, impacting user signup and consent completion rates.

## Decision

Replace the entire OTP stack with [Arkesel's OTP API](https://arkesel.com/phone-number-verification/):

- **Send OTP:** `POST https://sms.arkesel.com/api/v2/otp/send` — Arkesel generates, stores, and delivers the OTP
- **Verify OTP:** `POST https://sms.arkesel.com/api/v2/otp/verify` — Arkesel validates the code server-side

Arkesel handles: cryptographic generation, server-side storage, configurable expiry, per-number rate limiting, brute-force protection, and SMS delivery with automatic voice/USSD fallback.

### What we remove

- `OTPRequest` model and its DB table (drop in a migration)
- OTP generation in `AuthService.send_otp()` (`secrets.choice`)
- OTP hashing with `make_password` and argon2
- OTP expiry logic (cached `_OTP_TTL_SECONDS` + DB `expires_at`)
- OTP rate limiting (hourly counters, cache lock keys)
- OTP verification in `AuthService.verify_otp()` (lookup + hash compare)
- `SmsGateway` class (Africa Talking) — kept as file for reference but no longer active
- `send_sms_message` Celery task — replaced by `send_otp_message` task calling Arkesel

### What we keep

- Celery async pattern — wrap Arkesel calls in tasks for retries + fire-and-forget
- Audit events — still record `auth.otp_sent`, `auth.otp_verified`, etc.
- Session creation — unchanged

### New files

- `infrastructure/sms/arkesel_client.py` — `ArkeselOtpClient` with `send_otp()` and `verify_otp()`

### Changed files

- `apps/auth/services.py` — delegate to Arkesel, remove local OTP management
- `apps/consent/services.py` — use Arkesel verify for consent OTP
- `apps/notifications/tasks.py` — new Celery task for Arkesel send
- `config/settings/base.py` — add `ARKESEL_API_KEY`, `ARKESEL_SENDER_ID`
- `config/settings/production.py` — add arkesel runtime validation
- `.env.example` — document Arkesel vars, demote Africa Talking
- `apps/health/api/views.py` — arkesel health check

## Consequences

### Positive

- Eliminates ~100 lines of custom OTP management (generation, hashing, storage, expiry, rate limiting)
- Arkesel handles multi-channel delivery with automatic SMS→Voice→USSD fallback
- Better deliverability via direct MNO connections in Ghana
- Arkesel manages security (rate limiting, brute-force protection) — reduces audit surface
- GHS 0.035/OTP, no monthly fee

### Negative

- External dependency — OTP availability depends on Arkesel uptime
- Cannot verify OTPs during an Arkesel outage (no local fallback)
- Adding a new provider integration (initial setup cost)
- Sender ID registration takes a few business days (Ghana)

### Neutral

- OTP flow logic remains in Celery tasks (same async pattern)
- Audit events unchanged — same event types, same service
