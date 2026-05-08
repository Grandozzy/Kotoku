# PDF Generation Optimization Design

## Problem

PDF generation for sealed agreements gets stuck at `GENERATING` status indefinitely. The Celery task dies silently without updating the vault entry status. Users must reload the page and retry. Additionally, the current PDF content is minimal and the generation is manually triggered instead of automatic.

## Root Cause Analysis

1. **Silent task failures** — `generate_pdf_export` Celery task has no top-level try/except. Unhandled exceptions (S3 timeouts, data errors, worker crashes) leave `pdf_status=GENERATING` forever.
2. **No timeout** — Task has no `time_limit` or `soft_time_limit`, so a stuck task runs indefinitely.
3. **No recovery mechanism** — No periodic check for stuck entries, no retry endpoint for FAILED entries.
4. **Manual trigger** — PDF generation requires a separate `POST /vault/{id}/export/` call instead of auto-generating on seal.
5. **Polling-based status** — Frontend polls for status changes instead of receiving push notifications.

## Design

### 1. Reliability Fixes

#### Bulletproof Celery Task

Wrap entire task body in try/except. Every exception path calls `mark_pdf_failed()`:

```
generate_pdf_export(entry_id):
    try:
        entry = load_vault_entry(entry_id)
        mark GENERATING
        push WS "vault.pdf_generating"
        pdf_bytes = render_vault_pdf(entry)
        url = s3_upload(pdf_bytes)
        mark READY with url
        push WS "vault.pdf_ready"
    except Exception:
        mark FAILED
        push WS "vault.pdf_failed"
        self.retry(exc=exc)
```

#### Task Timeouts

Add `time_limit=120, soft_time_limit=90` to the task decorator. The soft limit raises `SoftTimeLimitExceeded` which the try/except catches, marks FAILED, and pushes WS notification.

#### on_failure Handler

Add class-level `on_failure` method to catch worker-level crashes (OOM, SIGKILL):

```
@classmethod
def on_failure(cls, exc, task_id, args, kwargs, einfo):
    entry_id = args[0]
    VaultService.mark_pdf_failed(entry_id)
    push WS "vault.pdf_failed" to all parties
```

#### Stuck Task Recovery (Beat Periodic Task)

New Celery Beat task runs every 5 minutes:

```
recover_stuck_pdf_generating():
    entries = VaultEntry.filter(
        pdf_status=GENERATING,
        updated_at__lt=now() - 5 minutes
    )
    for each entry:
        mark FAILED
        push WS "vault.pdf_failed" to all parties
```

#### Retry Endpoint

`POST /api/vault/{agreement_id}/retry-export/`

- Only works when `pdf_status` is `FAILED`
- Resets to `PENDING`, then triggers `generate_pdf_export.delay()`
- Returns 409 if status is not FAILED

### 2. Auto-Generate on Seal

Modify `VaultService.create_for_agreement()` to auto-enqueue PDF generation:

```
create_for_agreement(agreement):
    entry = get_or_create VaultEntry(agreement=agreement, pdf_status=PENDING)
    if created or entry.pdf_status in (PENDING, FAILED):
        generate_pdf_export.delay(entry.pk)
    return entry
```

On re-seal (agreement reopened then sealed again):
- Existing VaultEntry is reused
- `pdf_status` reset to `PENDING`
- New PDF generated (overwrites old S3 object)

The existing `/export/` endpoint is repurposed as a manual re-generate endpoint (for any status).

### 3. WebSocket Push for PDF Status

#### New Event Types

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `vault.pdf_generating` | Task starts rendering | `{agreement_id}` |
| `vault.pdf_ready` | PDF uploaded to S3 | `{agreement_id, pdf_url}` |
| `vault.pdf_failed` | Task fails or stuck recovery | `{agreement_id}` |

#### Backend Changes

All three events sent via existing `send_to_user()` helper in `notifications/push.py`. Iterate over agreement parties (same pattern as `agreement.sealed`).

Sent from:
- `generate_pdf_export` task — on start, success, failure
- `on_failure` handler — on worker crash
- `recover_stuck_pdf_generating` Beat task — on stuck recovery

#### Frontend Changes

Update `INVALIDATION_MAP` in `useNotifications.ts`:

```typescript
"vault.pdf_ready": ["vault"],
"vault.pdf_failed": ["vault"],
"vault.pdf_generating": ["vault"],
```

On `vault.pdf_ready`, React Query invalidates `["vault"]` keys, triggering refetch. The vault entry now has `pdf_status=READY` and `pdf_url` populated. UI shows download link immediately.

On `vault.pdf_failed`, UI shows error state with retry button.

No polling needed. Status changes arrive in real-time via WebSocket.

### 4. Improved PDF Content

#### Current PDF (minimal)

- Header: "KOTOKU — SEALED AGREEMENT"
- Core fields: title, scenario, status, sealed date, description
- Parties table: role, name, ID type, ID number, phone
- Evidence table: type, file type, file hash (truncated to 16 chars)
- Footer: seal hash + disclaimer

#### Enhanced PDF

Add between evidence table and footer:

**Field Data Section** — Render `agreement.field_data` JSON as a styled key-value table. Each scenario template field gets a row with label and value. Empty fields omitted.

**Full Seal Hash** — Show complete 64-char SHA-256 hash, not truncated. Wrapped in a monospace paragraph.

**Revision History** — Query `AgreementRevision` objects for this agreement. Render as a timeline table: revision number, sealed date, seal hash (full), reason (if stored). Only present if revisions exist.

**Annotation Summary** — Query `Annotation` objects. Render as a table: annotation text, author name, created date. Only present if annotations exist.

#### Typography Improvements

- Increase spacing between sections (12pt spacer → 18pt)
- Add section dividers with labels ("PARTIES", "EVIDENCE", "AGREEMENT DETAILS", "REVISION HISTORY", "NOTES")
- Use a slightly larger base font (10pt → 10.5pt)
- Seal hash in monospace font for readability

### 5. Data Flow (Complete)

```
User seals agreement
  → POST /api/agreements/{id}/seal/
  → AgreementService.seal_agreement()
     → status → SEALED, compute seal_hash
     → send_to_user("agreement.sealed")        [EXISTING WS]
  → VaultService.create_for_agreement()
     → create VaultEntry (PENDING)
     → generate_pdf_export.delay(entry_id)      [NEW: AUTO-TRIGGER]
     → Frontend receives "agreement.sealed" WS event
     → UI shows sealed state, vault entry loading

Celery worker picks up task
  → mark GENERATING
  → send_to_user("vault.pdf_generating")        [NEW WS PUSH]
  → render_vault_pdf() with enriched content
     → field_data table
     → full seal hash
     → revision history (if any)
     → annotations (if any)
  → S3 upload
  → mark READY + pdf_url
  → send_to_user("vault.pdf_ready")             [NEW WS PUSH]
  → Frontend receives WS event
  → React Query invalidates "vault" cache
  → UI shows download link — NO POLLING

On failure:
  → mark FAILED
  → send_to_user("vault.pdf_failed")            [NEW WS PUSH]
  → self.retry() (up to 3 times, 60s delay)
  → Frontend shows error + retry button

Stuck recovery (every 5 min):
  → Beat task finds GENERATING entries older than 5 min
  → Marks FAILED
  → send_to_user("vault.pdf_failed")            [NEW WS PUSH]

Manual retry:
  → POST /api/vault/{id}/retry-export/
  → Re-enqueues Celery task
  → Same flow as above
```

## Files to Modify

| File | Change |
|------|--------|
| `apps/vault/tasks.py` | Bulletproof try/except, on_failure handler, WS pushes, timeouts |
| `apps/vault/services.py` | Auto-generate on create, retry endpoint logic, stuck recovery |
| `apps/vault/pdf.py` | Enriched content: field_data, full hash, revisions, annotations |
| `apps/vault/api/views.py` | Add retry-export endpoint |
| `apps/vault/api/urls.py` | Add retry URL route |
| `config/settings/base.py` | Add Beat schedule for stuck recovery task |
| Frontend `useNotifications.ts` | Add vault events to INVALIDATION_MAP |

## Success Criteria

1. PDF status never stuck at `GENERATING` for more than 6 minutes (5 min recovery + 1 min buffer)
2. PDF auto-generates on seal — no manual trigger needed
3. Frontend receives PDF status changes via WebSocket — no polling
4. Failed generations show error state with retry option
5. PDF includes field data, full seal hash, revision history, and annotations
6. All existing tests pass, new tests cover failure paths
