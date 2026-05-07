# Edit-and-Re-Seal Design Spec

**Date:** 2026-05-07
**Status:** Draft
**Scope:** Enable editing and re-sealing of agreements after bilateral reopen

---

## Problem

After bilateral reopen (SEALED → REOPEN_REQUESTED → ACTIVE), the agreement is in ACTIVE status with no path to edit or re-seal. The vault shows "Active" but there's no way to:
1. Navigate to edit the agreement
2. Re-seal after editing

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Edit scope | All fields editable | Parties, details, evidence can all change |
| Re-seal consent | Full bilateral OTP | Same trust model as original seal |
| Who can edit | Either party | Both confirmed reopen, either can edit |
| Edit UI | Reuse existing step flow | Familiar UX, minimal new code |
| Revision history | Store snapshots | Preserve sealed version for audit |
| Re-seal path | Reuse request_consent | Add ACTIVE → PENDING_CONSENT transition |

## Lifecycle

```
SEALED → request_reopen → REOPEN_REQUESTED → bilateral_confirm → ACTIVE
ACTIVE → (edit via step flow) → request_consent → PENDING_CONSENT → seal → SEALED
```

---

## Backend Changes

### 1. New Model: AgreementRevision

**File:** `apps/agreements/models.py`

```python
class AgreementRevision(models.Model):
    """Snapshot of agreement state at seal time, preserved before reopening."""

    agreement = models.ForeignKey(
        Agreement,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    seal_hash = models.CharField(max_length=64)
    sealed_at = models.DateTimeField()
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("agreement", "revision_number")]
        ordering = ["-revision_number"]

    def __str__(self) -> str:
        return f"Revision {self.revision_number} of {self.agreement}"
```

The `snapshot` JSONField stores:
```json
{
  "title": "...",
  "description": "...",
  "scenario_template": "...",
  "parties": [{"role": "buyer", "display_name": "...", "id_type": "...", "id_number": "...", "phone": "..."}],
  "evidence": [{"evidence_type": "...", "file_hash": "...", "file_key": "..."}]
}
```

### 2. State Machine: Add ACTIVE → PENDING_CONSENT

**File:** `apps/agreements/domain/state_machine.py`

Add transition:
```python
(AgreementStatus.ACTIVE, "request_consent"): AgreementStatus.PENDING_CONSENT,
```

### 3. Modify `can_request_consent` Policy

**File:** `apps/agreements/domain/policies.py`

Add ACTIVE to allowed statuses:
```python
def can_request_consent(agreement) -> bool:
    return agreement.status in {
        AgreementStatus.DRAFT,
        AgreementStatus.PENDING_CONSENT,
        AgreementStatus.ACTIVE,  # re-seal path
    } and agreement.parties.count() >= 2
```

### 4. New Service Method: `AgreementService.update_active()`

**File:** `apps/agreements/services.py`

```python
@staticmethod
def update_active(*, agreement_id: int, title: str | None = None,
                  description: str | None = None,
                  scenario_template: str | None = None) -> Agreement:
    agreement = Agreement.objects.get(pk=agreement_id)
    if agreement.status != AgreementStatus.ACTIVE:
        raise DomainError("Can only update an active (reopened) agreement")
    update_fields = ["updated_at"]
    if title is not None:
        agreement.title = title
        update_fields.append("title")
    if description is not None:
        agreement.description = description
        update_fields.append("description")
    if scenario_template is not None:
        agreement.scenario_template = scenario_template
        update_fields.append("scenario_template")
    agreement.save(update_fields=update_fields)
    AuditService.record_event(
        event_type="agreement.updated_active",
        entity_type="agreement",
        entity_id=str(agreement.pk),
        metadata={"updated_fields": update_fields},
    )
    return agreement
```

### 5. Modify PATCH Endpoint

**File:** `apps/agreements/api/views.py`

In `AgreementDetailView.patch()`, route based on status:
```python
if agreement.status == AgreementStatus.DRAFT:
    agreement = AgreementService.update_draft(agreement_id=agreement_id, **validated_data)
elif agreement.status == AgreementStatus.ACTIVE:
    agreement = AgreementService.update_active(agreement_id=agreement_id, **validated_data)
else:
    raise DomainError("Cannot update agreement in this status")
```

### 6. Extend Party/Evidence Endpoints for ACTIVE

Currently `add_party` and party/evidence mutations only work in DRAFT status. Add ACTIVE as an allowed status for:
- Adding/updating parties (for reopening edits)
- Uploading/removing evidence items

### 7. Modify ConsentService.request_otp for ACTIVE

**File:** `apps/consent/services.py`

The `request_otp` method currently requires `PENDING_CONSENT` status via `can_request_consent`. With the policy change above (allowing ACTIVE), the method needs to handle the ACTIVE → PENDING_CONSENT transition:

```python
# In request_otp, after can_request_consent check:
if agreement.status == AgreementStatus.ACTIVE:
    agreement.status = next_state(agreement.status, "request_consent")
    agreement.save(update_fields=["status", "updated_at"])
    AuditService.record_event(
        event_type="agreement.reseal_consent_requested",
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
```

### 8. Create Revision Snapshot on Bilateral Reopen

**File:** `apps/agreements/services.py`

In `complete_bilateral_reopen`, before clearing seal fields:

```python
# Create revision snapshot before clearing seal data
AgreementRevision.objects.create(
    agreement=agreement,
    revision_number=AgreementRevision.objects.filter(agreement=agreement).count() + 1,
    seal_hash=agreement.seal_hash,
    sealed_at=agreement.sealed_at,
    snapshot=_build_snapshot(agreement),
)
```

Where `_build_snapshot` extracts parties and evidence into the JSON format described above.

### 9. API Endpoints Summary

| Endpoint | Method | Change |
|----------|--------|--------|
| `/api/agreements/{id}/` | PATCH | Route to `update_active` for ACTIVE status |
| `/api/agreements/{id}/parties/` | POST | Allow in ACTIVE status |
| `/api/agreements/{id}/parties/{pk}/` | PATCH/PUT | Allow in ACTIVE status |
| `/api/agreements/{id}/evidence/` | POST | Allow in ACTIVE status |
| `/api/agreements/{id}/evidence/{pk}/` | DELETE | Allow in ACTIVE status |
No new endpoints needed. The existing consent and seal flows are reused:

- `/api/agreements/{id}/consent/request-otp/` — issues CONSENT-purpose OTPs, transitions ACTIVE → PENDING_CONSENT (after policy change)
- `/api/agreements/{id}/consent/confirm/` — verifies OTP, stays in PENDING_CONSENT
- `/api/agreements/{id}/seal/` — seals from PENDING_CONSENT → SEALED

---

## Frontend Changes

### 1. Vault Detail: "Edit Agreement" Button

**File:** `app/(main)/vault/[agreementId].tsx`

When `agreementStatus === "active"`, show a prominent "Edit agreement" button that navigates to the step flow:

```tsx
{record.agreementStatus === "active" && (
  <Button
    title="Edit agreement"
    variant="primary"
    size="lg"
    fullWidth
    onPress={() => router.push(`/agreement/${record.agreementId}/steps/parties?reopened=1`)}
  />
)}
```

### 2. Agreement Store: `isReopened` Flag

**File:** `src/features/agreements/agreementStore.ts`

Add:
```typescript
isReopened: boolean;
setIsReopened: (v: boolean) => void;
```

When navigating from vault with `?reopened=1`, set `isReopened = true`.

### 3. Step Flow Modifications for Re-Edit Mode

**File:** `app/agreement/[id]/steps/_layout.tsx`

When `isReopened` is true:
- Show banner: "Re-editing agreement — Make changes and re-seal"
- Step progress header shows "Re-edit" instead of "Create"

### 4. Step Screens: Allow Skipping

For re-edit mode, each step screen should:
- Pre-populate fields with existing data
- Show "Next" / "Save & continue" instead of requiring all fields fresh
- Allow navigating between steps freely (not strictly sequential)

### 5. Consent Step: "Re-seal" Labels

**File:** `app/agreement/[id]/steps/consent.tsx`

When `isReopened` is true:
- Title: "Re-seal agreement"
- Description: "Both parties must confirm with a one-time code before the agreement can be re-sealed."
- Button: "Re-seal agreement" instead of "Seal agreement"

### 6. Post-Seal Screen

**File:** `app/agreement/[id]/sealed.tsx`

When `isReopened` is true:
- Title: "Agreement re-sealed"
- Success message: "Your agreement has been updated and re-sealed."
- CTA: "View in vault" (same as now)

### 7. Vault Card: Active Badge

**File:** `src/components/vault/VaultCard.tsx`

Already handled — shows "Active" badge for `agreementStatus === "active"`.

### 8. Frontend Types Update

**File:** `src/types/vault.ts`

The `AgreementStatus` type already includes `"active"`. No changes needed.

**File:** `src/types/agreement.ts`

Add `"active"` to `AgreementStatus` type (currently missing).

---

## Data Flow: Complete Re-Edit Lifecycle

```
1. User taps "Request reopen" on sealed agreement
   → POST /agreements/{id}/reopen-request/
   → Status: REOPEN_REQUESTED

2. Both parties confirm OTPs
   → POST /agreements/{id}/reopen-consent/confirm/
   → Backend: creates AgreementRevision, clears seal fields
   → Status: ACTIVE

3. User taps "Edit agreement" in vault detail
   → Navigate to /agreement/{id}/steps/parties?reopened=1
   → Frontend sets isReopened = true

4. User edits parties, details, evidence
   → PATCH /agreements/{id}/ (calls update_active)
   → POST/PATCH parties, evidence (allowed in ACTIVE status)
  → Status remains: ACTIVE

5. User proceeds to consent step, requests re-seal codes
   → POST /agreements/{id}/request-consent/  (or equivalent)
   → Status: PENDING_CONSENT

6. Both parties confirm consent OTPs
   → POST consent verify
   → Status: PENDING_CONSENT (all consented)

7. User taps "Re-seal agreement"
   → POST /agreements/{id}/seal/
   → Backend: computes new seal_hash, sets sealed_at
   → Status: SEALED
```

---

## Migration Plan

### Backend Migration

```python
# 0004_agreement_revision_and_active_consent

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("agreements", "0003_sprint6_annotation_and_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgreementRevision",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("revision_number", models.PositiveIntegerField()),
                ("seal_hash", models.CharField(max_length=64)),
                ("sealed_at", models.DateTimeField()),
                ("snapshot", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("agreement", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="revisions",
                    to="agreements.agreement",
                )),
            ],
            options={
                "ordering": ["-revision_number"],
            },
        ),
        migrations.AddIndex(
            model_name="agreementrevision",
            index=models.Index(fields=["agreement", "revision_number"],
                             name="uniq_agreement_revision"),
        ),
    ]
```

Note: The unique_together constraint on (agreement, revision_number) is handled in the model Meta.

---

## Edge Cases

| Case | Handling |
|------|----------|
| Concurrent edits by both parties | Last write wins. Both parties have the agreement open, the PATCH that lands last persists. |
| User edits but doesn't re-seal | Agreement stays in ACTIVE status. Vault shows "Active — Edit in progress" |
| Re-seal OTPs expire | User can re-request OTPs (existing flow) |
| Multiple reopens | Each reopen creates a new AgreementRevision with incrementing revision_number |
| Someone tries to edit DRAFT with update_active | Blocked — `update_active` only works for ACTIVE status |
| Someone tries to edit SEALED agreement | Blocked — PATCH endpoint checks status and rejects |
| Cancel reopen (REOPEN_REQUESTED → SEALED) | No revision created (reopen was cancelled before completing) |

---

## Out of Scope

- Cancel-reopen API endpoint (already exists as service method)
- Legacy single-party reopen API (not in scope)
- Admin UI for viewing revision history
- Diff view comparing revisions
- Limiting which fields can be edited (all are editable per decision)