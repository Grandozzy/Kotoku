# Seed Script + Console SMS Backend

**Date:** 2026-05-06
**Issue:** #7
**Branch:** `feat/seed-script-and-auth-flow`

## Goal

Enable repeatable on-device testing with a `manage.py seed_test_data` command and a console-backed SMS gateway that prints OTPs to the terminal during development.

## Console SMS Backend

### New file: `infrastructure/sms/console_gateway.py`

`ConsoleSmsGateway` with the same `send(to, body) -> bool` interface as `SmsGateway`. Extracts the OTP from the message body via regex and prints a formatted line to stdout:

```
📱 SMS to +233500000001: "Your Kotoku verification code is 12345678. Valid for 10 minutes."
   OTP: 12345678
```

### Settings factory

In `config/settings/base.py`, add:

```python
SMS_BACKEND = os.getenv("SMS_BACKEND", "africastalking")
```

Add a module-level `get_sms_gateway()` function in `infrastructure/sms/__init__.py` (or `gateway.py`) that returns `ConsoleSmsGateway` when `settings.SMS_BACKEND == "console"`, otherwise `SmsGateway()`.

### Call site updates

Replace direct `SmsGateway()` instantiation in these 3 locations with `get_sms_gateway()`:

1. `apps/auth/services.py` — `AuthService.send_otp()`
2. `apps/consent/services.py` — `ConsentService.request_otp()` / `request_reopen_otp()`
3. `apps/notifications/providers/sms_provider.py` — `SmsNotificationProvider`

When `SMS_BACKEND` is unset or `africastalking`, behavior is identical to current code.

## Seed Command

### File: `apps/templates/management/commands/seed_test_data.py`

Placed alongside the existing `seed_templates` command.

### What it creates

| Resource | Details |
|----------|---------|
| 2 Users | Alice (`+233500000001`), Bob (`+233500000002`) via `get_or_create` |
| 2 Accounts | With emails and full names |
| 2 IdentityRecords | Ghana Card type (`GHA-000000001`, `GHA-000000002`) |
| 1 Agreement | Draft cash-sale: "Cash Sale - Toyota Corolla 2020" |
| 2 Parties | buyer=Alice, seller=Bob |
| 2 DRF Tokens | Via `Token.objects.get_or_create` |

Calls `call_command("seed_templates")` first to ensure scenario templates exist.

### `--sealed` flag

Runs the full consent flow:

1. For each party, call `ConsentService.request_otp()` — this stores OTP in Redis and calls SMS gateway
2. Read the OTP from Redis cache using the same key pattern the service uses (`consent_otp:{party_id}:{purpose}`)
3. Verify via `ConsentService.verify_consent_otp()`
4. Transitions agreement through `pending_consent → active → sealed`

### Output

Prints auth tokens, identity references, agreement ID, and API URLs to stdout so the tester can immediately start using the API:

```
🌱 Seeded test data
══════════════════════════════════════
Alice (+233500000001)
  Token: abc123...
  Identity: GHA-000000001

Bob (+233500000002)
  Token: def456...
  Identity: GHA-000000002

Agreement: "Cash Sale - Toyota Corolla 2020" (draft)
  GET /api/agreements/{id}/
══════════════════════════════════════
```

### Idempotency

All creates use `get_or_create`. Safe to re-run without errors.

## .env.example update

Add commented option:

```
# SMS_BACKEND=console   # Print OTPs to terminal instead of Africa's Talking
```

## Files changed

| File | Action |
|------|--------|
| `infrastructure/sms/console_gateway.py` | New |
| `infrastructure/sms/__init__.py` | New — export `get_sms_gateway` |
| `config/settings/base.py` | Edit — add `SMS_BACKEND` setting |
| `apps/auth/services.py` | Edit — use `get_sms_gateway()` |
| `apps/consent/services.py` | Edit — use `get_sms_gateway()` |
| `apps/notifications/providers/sms_provider.py` | Edit — use `get_sms_gateway()` |
| `apps/templates/management/commands/seed_test_data.py` | New |
| `.env.example` | Edit — add `SMS_BACKEND` option |

## Out of scope

- Changing the auth OTP flow (it already works)
- Modifying existing test infrastructure (the `autouse` mock in `conftest.py` stays)
- Frontend changes (that's issue #12)
