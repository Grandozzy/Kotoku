# Vault PDF Export + Audit Log

## Context

The full seal flow creates a VaultEntry on seal, but PDF export is not working end-to-end. The frontend also calls a missing audit-log endpoint. This design fixes both and upgrades seed data for production-faithful testing.

## Scope

1. Verify and fix the PDF export pipeline (Celery task + MinIO upload)
2. Add missing `GET /api/vault/{agreement_id}/audit-log/` endpoint
3. Upgrade seed data to upload real evidence file to MinIO
4. Add smoke test management command

## 1. PDF Pipeline Verification & Fix

**Current flow:**
```
ExportButton → POST /api/vault/{id}/export/ → Celery task → ReportLab PDF → MinIO upload → pdf_status=ready
```

**What to verify/fix:**
- `VaultExportView` triggers Celery task correctly
- `generate_pdf_export` task renders without errors with seed data
- MinIO upload succeeds and returns reachable URL
- Frontend `downloadAsync` can reach the MinIO URL from emulator/device

**If Celery task fails:** diagnose the specific failure (task registration, S3 config, ReportLab error) and fix inline.

## 2. Audit-Log Endpoint

**Endpoint:** `GET /api/vault/{agreement_id}/audit-log/`

**Returns a timeline of events** aggregated from existing models:

| Event type | Source model | Timestamp field |
|---|---|---|
| `agreement_created` | Agreement | `created_at` |
| `party_added` | Party | `created_at` |
| `evidence_uploaded` | EvidenceItem | `created_at` |
| `consent_requested` | ConsentRecord | `created_at` |
| `consent_confirmed` | ConsentRecord | `granted_at` |
| `sealed` | Agreement | `sealed_at` |
| `annotation_added` | Annotation | `created_at` |
| `dispute_raised` | Dispute | `created_at` |

**Response shape:**
```json
{
  "data": {
    "events": [
      {
        "type": "agreement_created",
        "timestamp": "2026-05-06T12:00:00Z",
        "actor": "Alice",
        "description": "Agreement created by Alice"
      }
    ]
  }
}
```

**Implementation:**
- New `VaultAuditLogView` in `apps/vault/api/views.py`
- `AuditEventSerializer` for event representation
- Query Agreement, Party, EvidenceItem, ConsentRecord, Annotation, Dispute
- Merge into sorted timeline (descending by timestamp)
- Ownership check: user must be a party on the agreement

## 3. Enhanced Seed Data

**Upgrade `seed_test_data.py --sealed`:**
- Generate a 1x1 PNG in code (minimal valid PNG bytes)
- Upload to MinIO via `S3StorageClient` with key `test-data/vehicle_front.png`
- Set `file_hash` to SHA-256 of the image bytes
- Set `storage_url` to the returned MinIO URL
- This gives the PDF a real file hash and a downloadable evidence file

## 4. Smoke Test Command

**New management command:** `test_vault_export`

- Finds the seeded sealed agreement's vault entry
- Calls `generate_pdf_export.apply()` synchronously
- Asserts `pdf_status == "ready"` and `pdf_url` is non-empty
- Prints success/failure with details

## Out of Scope

- Bilateral reopen flow
- Post-seal annotations flow
- Dispute flow
- Frontend changes (unless PDF URL format needs adjustment)
