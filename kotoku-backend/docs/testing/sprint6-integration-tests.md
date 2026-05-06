# Sprint 6 Integration Tests — Manual Verification Guide

Issues #8–#11. All 18 tests live in `tests/integration/`.

Run them:

```bash
python -m pytest tests/integration/ -v
```

## Prerequisites

Docker containers running: `web` (:8000), `db` (:5433), `redis` (:6379), `minio` (:9000/9001).

```bash
docker compose exec web python manage.py seed_test_data --sealed
```

This prints token keys and agreement URL. Use the printed token for `Authorization: Token <key>` in all requests below.

OTPs appear in the `web` container logs because `SMS_BACKEND=console`.

---

## #8: Full Seal Flow → Vault Entry + PDF Export

**File:** `tests/integration/test_seal_flow.py` (3 tests)

### What it tests

The entire lifecycle from blank agreement to sealed document with PDF export.

### Manual steps

| Step | Action | Expected |
|------|--------|----------|
| 1 | `POST /api/agreements/` with `title`, `scenario_template: "used_vehicle_sale"` | 201, status=`DRAFT` |
| 2 | `POST /api/agreements/{id}/parties/` — add seller + buyer with Ghana Card IDs | 200 |
| 3 | Create evidence item — vehicle photo, `upload_status=CONFIRMED` | — |
| 4 | `POST /api/agreements/{id}/consent/request-otp/` | 201, 2 OTPs printed to console |
| 5 | `POST /api/agreements/{id}/consent/confirm/` with each party's `party_phone` + `otp_code` | 200, `granted: true` × 2 |
| 6 | `POST /api/agreements/{id}/seal/` | 200, status=`SEALED`, `sealed_at` set, `seal_hash` non-empty |
| 7 | Check vault entry exists | `GET /api/vault/{id}/` → `pdf_status: PENDING` |
| 8 | `POST /api/vault/{id}/export/` | 202, `pdf_status: GENERATING`, then `READY` with `pdf_url` |

### Audit events verified

`agreement.created` → `agreement.consent_requested` → `consent.granted` (×2) → `agreement.sealed` → `vault.entry_created` → `vault.export_requested` → `vault.export_ready`

### What the tests mock

- S3 upload (`S3StorageClient.upload`) — returns fake URL
- PDF rendering (`render_vault_pdf`) — returns fake bytes

State machine, consent flow, vault creation, audit logging, and all API validation run unmodified.

---

## #9: Bilateral Reopen Flow

**File:** `tests/integration/test_reopen_flow.py` (5 tests)

### What it tests

After sealing, one party requests reopen → both confirm via OTP → agreement becomes editable again.

### Manual steps

| Step | Action | Expected |
|------|--------|----------|
| 1 | Start from a **sealed agreement** (seed with `--sealed`) | status=`SEALED` |
| 2 | `POST /api/agreements/{id}/reopen-request/` | 200, status=`REOPEN_REQUESTED`, 2 OTPs printed |
| 3 | `POST /api/agreements/{id}/reopen-consent/confirm/` with first party's `phone` + `otp_code` | 200, `granted: true`, status still `REOPEN_REQUESTED` |
| 4 | Submit second party's OTP | 200, status=`ACTIVE`, `sealed_at=null`, `seal_hash=""` |

### Cancel reopen path

After step 2, instead of confirming:

| Step | Action | Expected |
|------|--------|----------|
| 5 | Call `AgreementService.cancel_reopen(agreement_id=...)` | status=`SEALED` (no edit) |

### OTP re-issue

| Step | Action | Expected |
|------|--------|----------|
| 6 | `POST /api/agreements/{id}/reopen-consent/request-otp/` | Wipes old OTPs, sends 2 fresh ones |

### Audit events verified

`agreement.reopen_requested` → `consent.reopen_otp_issued` (×2) → `consent.reopen_granted` (×2) → `agreement.reopened_bilateral`

---

## #10: Post-Seal Annotations

**File:** `tests/integration/test_annotation_flow.py` (5 tests)

### What it tests

Once sealed, parties can attach notes; non-parties and pre-seal states are blocked.

### Manual steps

| Step | Action | Expected |
|------|--------|----------|
| 1 | Start from a **sealed agreement** | — |
| 2 | `POST /api/agreements/{id}/annotations/` with `author_party_id` + `body` | 201, annotation returned |
| 3 | `GET /api/agreements/{id}/annotations/` | 200, array with your annotation |

### Negative cases

| Attempt | Expected |
|---------|----------|
| Non-party `author_party_id` | 400 ("author must be a party") |
| Annotating a DRAFT agreement | 400 ("only sealed or reopen-requested") |
| Another user's agreement | 404 |

### Ordering

Add 3 annotations → GET returns them in `created_at` order (first-in-first-out).

---

## #11: Dispute on Sealed Agreement

**File:** `tests/integration/test_dispute_flow.py` (5 tests)

### What it tests

A party can raise a dispute against a sealed agreement; validation blocks abuse.

### Manual steps

| Step | Action | Expected |
|------|--------|----------|
| 1 | Start from a **sealed agreement** | — |
| 2 | `POST /api/agreements/{id}/disputes/` with `raised_by_party_id` + `reason` (min 10 chars) | 201, status=`open` |
| 3 | `GET /api/agreements/{id}/disputes/` | 200, array with your dispute |

### Response fields verified

`id`, `raised_by_party_id`, `raised_by_display_name`, `reason`, `status`, `resolution` (empty), `resolved_at` (null), `created_at`

### Negative cases

| Attempt | Expected |
|---------|----------|
| Non-party `raised_by_party_id` | 400 ("must be a party on this agreement") |
| Disputing a DRAFT agreement | 400 ("only sealed, closed, or archived") |
| Another user's agreement | 404 |
| Reason shorter than 10 chars | 400 (serializer validation) |

---

## Quick manual test script

```bash
# Seed sealed agreement
docker compose exec web python manage.py seed_test_data --sealed

# Use the printed token:
export TOKEN="<token from seed output>"

# List agreements
curl -s -H "Authorization: Token $TOKEN" http://localhost:8000/api/agreements/ | python -m json.tool

# Check vault
curl -s -H "Authorization: Token $TOKEN" http://localhost:8000/api/vault/ | python -m json.tool

# Request reopen (OTP appears in web container logs)
curl -s -X POST -H "Authorization: Token $TOKEN" http://localhost:8000/api/agreements/<id>/reopen-request/

# Confirm reopen OTP (read OTP from logs)
curl -s -X POST -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+233500000001", "otp_code": "<otp from logs>"}' \
  http://localhost:8000/api/agreements/<id>/reopen-consent/confirm/

# Add annotation
curl -s -X POST -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"author_party_id": <party_id>, "body": "Keys handed over."}' \
  http://localhost:8000/api/agreements/<id>/annotations/

# Open dispute
curl -s -X POST -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"raised_by_party_id": <party_id>, "reason": "Vehicle condition does not match description."}' \
  http://localhost:8000/api/agreements/<id>/disputes/
```
