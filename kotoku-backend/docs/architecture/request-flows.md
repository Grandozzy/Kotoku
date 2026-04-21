# Request Flows

## 1. Agreement creation and party onboarding

```
Client                  API (AgreementService)          DB
  │                           │                          │
  │── POST /api/agreements/ ──▶                          │
  │                           │── Agreement.objects.create (DRAFT)
  │                           │── AuditService.record_event ────▶│
  │◀── 201 agreement_id ──────│                          │
  │                           │                          │
  │── POST /api/agreements/{id}/parties/ ──▶             │
  │                           │── Party.objects.create ─▶│
  │◀── 201 party_id ──────────│                          │
```

Repeat the party step for each participant. At least two parties are required before consent can be requested.

---

## 2. Consent flow (OTP-based)

```
Client            API (AgreementService / ConsentService)   Redis    SMS
  │                        │                                  │        │
  │── POST request_consent ▶                                  │        │
  │                        │── Agreement: DRAFT → PENDING_CONSENT      │
  │                        │── For each party:                │        │
  │                        │     generate 8-digit OTP         │        │
  │                        │     ConsentRecord.create          │        │
  │                        │     NotificationService.send ────────────▶│
  │◀── 200 records[] ──────│                                  │        │
  │                        │                                  │        │
  │  [party receives SMS]  │                                  │        │
  │                        │                                  │        │
  │── POST verify_otp ─────▶                                  │        │
  │   {consent_record_id,  │── rate-limit check ─────────────▶│        │
  │    otp_code}           │◀── attempt count ────────────────│        │
  │                        │── verify hash (constant-time)    │        │
  │                        │── ConsentRecord.granted = True    │        │
  │                        │── if all parties consented:       │        │
  │                        │     Agreement: PENDING_CONSENT → ACTIVE   │
  │◀── 200 record ─────────│                                  │        │
```

OTP rate limit: 3 failed attempts locks the record for 15 minutes (Redis cache key `otp_attempts:<id>`).

---

## 3. Evidence upload

```
Client             API (EvidenceService)       S3/MinIO
  │                       │                       │
  │── POST /evidence/ ────▶                       │
  │   {agreement_id,      │── validate file size  │
  │    party_id,          │── validate magic bytes│
  │    file_type,         │── SHA-256 hash        │
  │    file_data}         │── S3StorageClient.upload ────────▶│
  │                       │◀── storage_url ───────────────────│
  │                       │── EvidenceItem.create             │
  │                       │── AuditService.record_event       │
  │◀── 201 item ──────────│                       │
```

File validation enforced before any network call: empty files, files exceeding 50 MB, and files whose magic bytes don't match the declared `file_type` are rejected immediately.

---

## 4. Agreement sealing

```
Client       API (AgreementService)       DB
  │                 │                      │
  │── POST seal ───▶│                      │
  │                 │── select_for_update (Agreement) ──▶│
  │                 │── can_seal policy check:            │
  │                 │     status == ACTIVE?               │
  │                 │     evidence_items.exists()?        │
  │                 │── Agreement: ACTIVE → SEALED        │
  │                 │── sealed_at = now()                 │
  │                 │── AuditService.record_event ───────▶│
  │◀── 200 ────────│                      │
```

Reopening is available within 24 hours of sealing (reverts to ACTIVE). After 24 hours, only `close` is permitted.

---

## 5. Notification dispatch (async)

```
ConsentService          NotificationService      Celery worker    SmsGateway
      │                        │                       │               │
      │── send_notification() ─▶                       │               │
      │                        │── Notification.create  │               │
      │                        │── dispatch_notification.delay ────────▶│
      │                        │                       │── SmsGateway.send ──▶ Africa's Talking
      │                        │                       │── Notification.status = SENT/FAILED
```

Notifications are always created synchronously but dispatched asynchronously via Celery. This decouples the consent flow from SMS delivery latency.

---

## 6. Health and readiness probes

```
Load balancer / k8s
  │
  │── GET /api/health/      → 200 healthy / 503 unhealthy
  │── GET /api/health/readiness/ → 200 ready / 503 not_ready
```

Both probes check PostgreSQL (`SELECT 1`) and Redis (`PING`) with a 3-second timeout. Error details are logged server-side only; the response body exposes only `ok` or `error` per dependency to avoid leaking internal topology.
