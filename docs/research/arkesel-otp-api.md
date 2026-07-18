# Arkesel OTP API — Research Findings

Source: https://arkesel.com/phone-number-verification/

## Endpoints

### Send OTP
`POST https://sms.arkesel.com/api/v2/otp/send`

**Headers:** `api-key: YOUR_API_KEY`, `Content-Type: application/json`

**Request body:**
```json
{
  "expiry": 5,
  "length": 6,
  "medium": "sms",
  "message": "Your verification code is %otp_code%. It expires in 5 minutes.",
  "number": "+233244000000",
  "sender_id": "MyApp",
  "type": "numeric"
}
```

- `expiry`: minutes (1–30)
- `length`: digits (4–8)
- `medium`: `"sms"`, `"voice"`, or `"ussd"`
- `message`: template — `%otp_code%` placeholder replaced by Arkesel
- `number`: E.164 phone number
- `sender_id`: registered in Arkesel dashboard
- `type`: `"numeric"`

**Success response:** `200 OK` — `{"code":"1000","message":"Successful, OTP is being processed for delivery"}`

### Verify OTP
`POST https://sms.arkesel.com/api/v2/otp/verify`

**Request body:**
```json
{
  "code": "173882",
  "number": "+233244000000"
}
```

**Success response:** `200 OK` — `{"code":"1100","message":"Successful"}`
**Failure response:** `{"code":"1102","message":"Invalid code"}` (or similar error codes)

## What Arkesel manages for us

- Cryptographic OTP generation
- Server-side storage and expiry (no DB columns needed)
- Rate limiting per phone number
- Brute-force protection
- Delivery via SMS, Voice, or USSD (multi-channel auto-fallback)

## Sender ID registration

Register in Arkesel dashboard. Submit brand name + business registration.
- Ghana: carrier-level, a few business days
- Nigeria: network-level, 4–6 weeks for transactional

## Implications for Kotoku

**Removed from our stack:**
- OTP generation logic (`secrets.choice("0123456789")`)
- OTP hashing + DB storage (`OTPRequest` model, `make_password`)
- OTP expiry tracking (cached + DB `expires_at`)
- OTP rate limiting logic (lock keys, hourly counters)
- OTP verification logic (lookup + hash compare)
- `SmsGateway` class (Africa Talking)
- `send_sms_message` Celery task — replaced by Arkesel OTP client

**Kept:**
- Celery async pattern (wrap Arkesel calls in same fire-and-forget style)
- Audit events (`AuditService.record_event`)
- Session creation (`_create_session`)
- Consent OTP confirmation flow (becomes Arkesel verify instead of local verify)

**New:**
- `ArkeselOtpClient` class — thin wrapper over `/otp/send` and `/otp/verify`
- `send_otp_message` Celery task — calls `ArkeselOtpClient.send_otp()`
- `verify_otp` method — calls `ArkeselOtpClient.verify_otp()`

## Cost

GHS 0.035 per SMS/USSD OTP verification (no monthly fee, no minimum).
