# Edit-and-Re-Seal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable editing and re-sealing agreements after bilateral reopen, completing the lifecycle: SEALED → REOPEN_REQUESTED → ACTIVE → (edit) → PENDING_CONSENT → SEALED.

**Architecture:** Add an `AgreementRevision` model for audit snapshots, extend the state machine with ACTIVE→PENDING_CONSENT, add `update_active` service method, modify policies/consent to support re-seal, and update the frontend step flow to support re-edit mode.

**Tech Stack:** Django/DRF (backend), React Native/Expo (frontend), Zustand (state), TanStack Query (data fetching)

---

## File Structure

### Backend (new files)
- `apps/agreements/migrations/0004_agreement_revision_and_active_consent.py` — migration for AgreementRevision model + status change
- `apps/agreements/tests/test_edit_reseal.py` — test file for the edit-and-reseal flow

### Backend (modified files)
- `apps/agreements/models.py` — add AgreementRevision model
- `apps/agreements/domain/state_machine.py` — add ACTIVE→PENDING_CONSENT transition
- `apps/agreements/domain/policies.py` — allow ACTIVE in can_request_consent, update can_seal for reseal
- `apps/agreements/services.py` — add update_active(), create_revision on bilateral reopen, update seal logic for reseal
- `apps/agreements/api/serializers.py` — add AgreementRevisionSerializer
- `apps/agreements/api/views.py` — route PATCH to update_active for ACTIVE status
- `apps/parties/services.py` — allow ACTIVE status in set_parties/patch_parties
- `apps/consent/services.py` — handle ACTIVE status for request_otp reseal flow

### Frontend (modified files)
- `src/types/agreement.ts` — add "active" to AgreementStatus type
- `src/features/agreements/agreementStore.ts` — add isReopened flag + setIsReopened
- `src/features/agreements/useAgreementDraft.ts` — add useReactivateDraft hook
- `app/(main)/vault/[agreementId].tsx` — add "Edit agreement" button when active
- `app/agreement/[id]/steps/_layout.tsx` — show re-edit banner when isReopened
- `app/agreement/[id]/steps/consent.tsx` — "Re-seal agreement" label when isReopened
- `app/agreement/[id]/sealed.tsx` — "Agreement re-sealed" message when isReopened

---

### Task 1: Add AgreementRevision model

**Files:**
- Modify: `apps/agreements/models.py`

- [ ] **Step 1: Add AgreementRevision model to models.py**

Add after the `Annotation` class in `apps/agreements/models.py`:

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

- [ ] **Step 2: Run makemigrations and verify it creates the migration**

Run: `cd kotoku-backend && python manage.py makemigrations agreements`
Expected: Creates `0004_agreement_revision_...py`

- [ ] **Step 3: Commit**

```bash
git add apps/agreements/models.py kotoku-backend/apps/agreements/migrations/0004_*.py
git commit -m "feat: add AgreementRevision model for sealed state snapshots"
```

---

### Task 2: Add ACTIVE→PENDING_CONSENT state transition

**Files:**
- Modify: `apps/agreements/domain/state_machine.py`
- Modify: `apps/agreements/tests/test_state_machine.py`

- [ ] **Step 1: Write failing test for ACTIVE→PENDING_CONSENT transition**

Add to `apps/agreements/tests/test_state_machine.py` in the `TestNextState` class:

```python
def test_active_request_consent_goes_to_pending_consent(self):
    assert (
        next_state(AgreementStatus.ACTIVE, "request_consent")
        == AgreementStatus.PENDING_CONSENT
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_state_machine.py::TestNextState::test_active_request_consent_goes_to_pending_consent -v`
Expected: FAIL — `Invalid transition: cannot perform 'request_consent' from 'active'`

- [ ] **Step 3: Add the transition to state_machine.py**

In `apps/agreements/domain/state_machine.py`, add to the `_TRANSITIONS` dict after the `(AgreementStatus.PENDING_CONSENT, "seal")` line:

```python
    (AgreementStatus.ACTIVE, "request_consent"): AgreementStatus.PENDING_CONSENT,
```

- [ ] **Step 4: Run the failing test to verify it passes**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_state_machine.py::TestNextState::test_active_request_consent_goes_to_pending_consent -v`
Expected: PASS

- [ ] **Step 5: Remove ACTIVE→request_consent from invalid transition tests**

In `test_state_machine.py`, the parametrized invalid transitions include `(AgreementStatus.ACTIVE, "request_consent")`. Remove it from the parametrize list at line 71.

- [ ] **Step 6: Add ACTIVE valid_actions test**

Add to `TestValidActions` class:

```python
def test_active_actions(self):
    actions = valid_actions(AgreementStatus.ACTIVE)
    assert "seal" in actions
    assert "request_consent" in actions
```

- [ ] **Step 7: Run all state machine tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_state_machine.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add apps/agreements/domain/state_machine.py apps/agreements/tests/test_state_machine.py
git commit -m "feat: add ACTIVE→PENDING_CONSENT state transition for re-seal"
```

---

### Task 3: Update can_request_consent policy to allow ACTIVE

**Files:**
- Modify: `apps/agreements/domain/policies.py`
- Modify: `apps/agreements/tests/test_policies.py`

- [ ] **Step 1: Write failing test for can_request_consent with ACTIVE status**

Add to `apps/agreements/tests/test_policies.py` in `TestCanRequestConsent`:

```python
def test_returns_true_when_active_with_two_parties(self, db):
    account = _make_account("active_consent@test.com")
    agreement = _make_agreement(
        status=AgreementStatus.ACTIVE, created_by=account
    )
    _make_party(agreement, Party.Role.BUYER)
    _make_party(agreement, Party.Role.SELLER)
    assert can_request_consent(agreement) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_policies.py::TestCanRequestConsent::test_returns_true_when_active_with_two_parties -v`
Expected: FAIL — `can_request_consent` returns False for ACTIVE

- [ ] **Step 3: Update can_request_consent in policies.py**

In `apps/agreements/domain/policies.py`, change `can_request_consent` from:

```python
def can_request_consent(agreement) -> bool:
    if agreement.status not in (AgreementStatus.DRAFT, AgreementStatus.PENDING_CONSENT):
        return False
    return agreement.parties.count() >= 2
```

to:

```python
def can_request_consent(agreement) -> bool:
    if agreement.status not in (
        AgreementStatus.DRAFT,
        AgreementStatus.PENDING_CONSENT,
        AgreementStatus.ACTIVE,
    ):
        return False
    return agreement.parties.count() >= 2
```

- [ ] **Step 4: Run the failing test to verify it passes**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_policies.py::TestCanRequestConsent::test_returns_true_when_active_with_two_parties -v`
Expected: PASS

- [ ] **Step 5: Run all policy tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_policies.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add apps/agreements/domain/policies.py apps/agreements/tests/test_policies.py
git commit -m "feat: allow can_request_consent for ACTIVE status (re-seal)"
```

---

### Task 4: Add update_active service method and create_revision on bilateral reopen

**Files:**
- Modify: `apps/agreements/services.py`
- Create: `apps/agreements/tests/test_edit_reseal.py`

- [ ] **Step 1: Write failing tests for update_active and revision creation**

Create `apps/agreements/tests/test_edit_reseal.py`:

```python
import pytest
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement, AgreementRevision
from apps.agreements.services import AgreementService
from apps.evidence.models import EvidenceItem
from apps.identity.models import IdentityRecord
from apps.parties.models import Party
from common.exceptions import DomainError

_seq = 0


def _account(email="test@test.com"):
    global _seq
    _seq += 1
    user = User.objects.create_user(phone=f"+233{_seq:09d}")
    return Account.objects.create(user=user, email=email, phone=user.phone)


def _identity(account, ref="ref-1"):
    return IdentityRecord.objects.create(
        account=account,
        reference=ref,
        verification_type="ghana_card",
    )


def _make_sealed_agreement():
    account = _account("sealed_edit@test.com")
    agreement = AgreementService.create_draft(
        title="Test Agreement",
        created_by=account,
        description="Original description",
    )
    id1 = _identity(account, "ref-a")
    id2 = IdentityRecord.objects.create(
        account=account, reference="ref-b", verification_type="phone"
    )
    Party.objects.create(
        agreement=agreement, identity=id1, role="buyer", display_name="Buyer"
    )
    Party.objects.create(
        agreement=agreement, identity=id2, role="seller", display_name="Seller"
    )
    agreement.status = AgreementStatus.SEALED
    agreement.sealed_at = timezone.now()
    agreement.seal_hash = "a" * 64
    agreement.save()
    return agreement


class TestUpdateActive:
    def test_update_active_updates_fields(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        updated = AgreementService.update_active(
            agreement_id=agreement.pk,
            title="Updated Title",
            description="Updated description",
        )
        assert updated.title == "Updated Title"
        assert updated.description == "Updated description"
        assert updated.status == AgreementStatus.ACTIVE

    def test_update_active_raises_if_not_active(self, db):
        account = _account("notactive@test.com")
        agreement = AgreementService.create_draft(title="T", created_by=account)
        with pytest.raises(DomainError, match="active"):
            AgreementService.update_active(
                agreement_id=agreement.pk, title="Nope"
            )

    def test_update_active_emits_audit_event(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.ACTIVE
        agreement.save()
        AgreementService.update_active(
            agreement_id=agreement.pk, title="Updated"
        )
        from apps.audit.models import AuditLog
        assert AuditLog.objects.filter(
            event_type="agreement.updated_active",
            entity_id=str(agreement.pk),
        ).exists()


class TestAgreementRevision:
    def test_revision_created_on_bilateral_reopen(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        original_sealed_at = agreement.sealed_at
        original_seal_hash = agreement.seal_hash

        reopened = AgreementService.complete_bilateral_reopen(
            agreement_id=agreement.pk
        )

        assert reopened.status == AgreementStatus.ACTIVE
        assert reopened.sealed_at is None
        assert reopened.seal_hash == ""

        revision = AgreementRevision.objects.get(agreement=agreement)
        assert revision.revision_number == 1
        assert revision.seal_hash == original_seal_hash
        assert revision.sealed_at == original_sealed_at
        assert "parties" in revision.snapshot
        assert "evidence" in revision.snapshot

    def test_multiple_revisions_increment(self, db):
        agreement = _make_sealed_agreement()

        # First reopen cycle
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)

        # Re-seal
        agreement.refresh_from_db()
        agreement.status = AgreementStatus.PENDING_CONSENT
        agreement.save()
        AgreementService.seal_agreement(agreement_id=agreement.pk)

        # Second reopen cycle
        agreement.refresh_from_db()
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)

        revisions = AgreementRevision.objects.filter(agreement=agreement).order_by(
            "revision_number"
        )
        assert revisions.count() == 2
        assert revisions[0].revision_number == 1
        assert revisions[1].revision_number == 2
```

- [ ] **Step 2: Run test to verify failures**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_edit_reseal.py -v`
Expected: FAIL — `AgreementService.update_active` doesn't exist yet, `AgreementRevision` doesn't exist yet

- [ ] **Step 3: Add `update_active` method to `AgreementService`**

In `apps/agreements/services.py`, add after the `update_draft` method:

```python
@staticmethod
def update_active(
    *,
    agreement_id: int,
    title: str | None = None,
    description: str | None = None,
    scenario_template: str | None = None,
) -> Agreement:
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

- [ ] **Step 4: Add `_build_snapshot` helper and modify `complete_bilateral_reopen` to create revision**

Add the `_build_snapshot` function before `AgreementService` in `services.py`:

```python
def _build_snapshot(agreement) -> dict:
    parties = list(
        agreement.parties.order_by("role").values(
            "role", "display_name", "id_type", "id_number", "phone"
        )
    )
    evidence = list(
        agreement.evidence_items.filter(upload_status="confirmed")
        .order_by("evidence_type", "file_key")
        .values("evidence_type", "file_hash", "file_key")
    )
    return {
        "agreement_id": agreement.pk,
        "title": agreement.title,
        "description": agreement.description,
        "scenario_template": agreement.scenario_template,
        "parties": parties,
        "evidence": evidence,
    }
```

Add import for `AgreementRevision` at top of `services.py`:

```python
from apps.agreements.models import Agreement, AgreementRevision
```

Modify `complete_bilateral_reopen` to create a revision before clearing seal fields:

```python
@staticmethod
@transaction.atomic
def complete_bilateral_reopen(*, agreement_id: int) -> Agreement:
    agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
    new_status = next_state(agreement.status, "bilateral_confirm")
    snapshot_data = _build_snapshot(agreement)
    revision_number = AgreementRevision.objects.filter(
        agreement=agreement
    ).count() + 1
    AgreementRevision.objects.create(
        agreement=agreement,
        revision_number=revision_number,
        seal_hash=agreement.seal_hash,
        sealed_at=agreement.sealed_at,
        snapshot=snapshot_data,
    )
    agreement.status = new_status
    agreement.sealed_at = None
    agreement.seal_hash = ""
    agreement.save(update_fields=["status", "sealed_at", "seal_hash", "updated_at"])
    AuditService.record_event(
        event_type="agreement.reopened_bilateral",
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
    return agreement
```

- [ ] **Step 5: Run the tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_edit_reseal.py -v`
Expected: All PASS

- [ ] **Step 6: Run the existing service tests to check for regressions**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_services.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add apps/agreements/services.py apps/agreements/tests/test_edit_reseal.py
git commit -m "feat: add update_active service method and revision snapshots on bilateral reopen"
```

---

### Task 5: Route PATCH endpoint for ACTIVE agreements and allow party/evidence edits

**Files:**
- Modify: `apps/agreements/api/views.py`
- Modify: `apps/parties/services.py`

- [ ] **Step 1: Update PATCH handler in views.py**

In `apps/agreements/api/views.py`, modify `AgreementDetailView.patch` (lines 80-92) to route based on status:

```python
def patch(self, request, agreement_id: int):
    agreement = self._get_agreement(
        agreement_id,
        account_id=request.user.account.pk,
        account_phone=request.user.account.phone,
    )
    serializer = AgreementUpdateSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    if agreement.status == AgreementStatus.DRAFT:
        agreement = AgreementService.update_draft(
            agreement_id=agreement_id,
            **serializer.validated_data,
        )
    elif agreement.status == AgreementStatus.ACTIVE:
        agreement = AgreementService.update_active(
            agreement_id=agreement_id,
            **serializer.validated_data,
        )
    else:
        raise DomainError("Cannot update agreement in this status")
    return ok({"agreement": AgreementDetailSerializer(agreement).data})
```

Add the `AgreementStatus` import check — it's already imported at line 12.

- [ ] **Step 2: Update `set_parties` and `patch_parties` in parties/services.py**

In `apps/parties/services.py`, modify `set_parties` (line 29) from:

```python
if agreement.status == AgreementStatus.SEALED:
    raise DomainError("Cannot modify parties of a sealed agreement.")
```

to:

```python
if agreement.status not in (AgreementStatus.DRAFT, AgreementStatus.ACTIVE):
    raise DomainError("Cannot modify parties: agreement is not in an editable state.")
```

Similarly for `patch_parties` (line 83), change from:

```python
if agreement.status == AgreementStatus.SEALED:
    raise DomainError("Cannot modify parties of a sealed agreement.")
```

to:

```python
if agreement.status not in (AgreementStatus.DRAFT, AgreementStatus.ACTIVE):
    raise DomainError("Cannot modify parties: agreement is not in an editable state.")
```

- [ ] **Step 3: Update evidence service to allow ACTIVE status**

In `apps/evidence/services.py`, modify `generate_upload_url` (line 161-162) from:

```python
if agreement.status == AgreementStatus.SEALED:
    raise DomainError("Cannot add evidence to a sealed agreement.")
```

to:

```python
if agreement.status not in (AgreementStatus.DRAFT, AgreementStatus.PENDING_CONSENT, AgreementStatus.ACTIVE):
    raise DomainError("Cannot add evidence: agreement is not in an editable state.")
```

- [ ] **Step 4: Update the `can_seal` policy for re-seal from PENDING_CONSENT**

In `apps/agreements/domain/policies.py`, update `can_seal` to handle the re-seal case. When sealing from PENDING_CONSENT (which came from ACTIVE via request_consent), all CONSENT-purpose records must be granted. The existing check already works for CONSENT records, but we need to make sure it only checks CONSENT-purpose records (not REOPEN):

Currently `can_seal` checks `ConsentSelector.all_parties_consented(agreement_id=agreement.pk)`. Verify this checks CONSENT-purpose only. If it checks all purposes, add a filter.

Read `apps/consent/selectors.py` to verify.

- [ ] **Step 5: Run the API test suite**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_agreement_api.py apps/parties/tests/test_parties_api.py apps/parties/tests/test_parties_service.py -v`
Expected: All PASS (may need minor fixes for changed error messages)

- [ ] **Step 6: Commit**

```bash
git add apps/agreements/api/views.py apps/parties/services.py apps/evidence/services.py apps/agreements/domain/policies.py
git commit -m "feat: allow ACTIVE agreement updates for re-edit and party/evidence changes"
```

---

### Task 6: Update consent service for re-seal OTP flow

**Files:**
- Modify: `apps/consent/services.py`

- [ ] **Step 1: Update `request_otp` to handle ACTIVE→PENDING_CONSENT transition**

In `apps/consent/services.py`, the `request_otp` method currently requires PENDING_CONSENT status (via `can_request_consent`). After our policy change, ACTIVE is also allowed. But we need to add the state transition ACTIVE→PENDING_CONSENT.

In the `request_otp` method, find the block that handles `PENDING_CONSENT` status (around line 156-172). Modify the `else` branch that transitions from DRAFT to PENDING_CONSENT, to also handle ACTIVE:

Currently the method has this logic:
```python
if agreement.status == AgreementStatus.PENDING_CONSENT:
    # ... re-issue logic
else:
    # ... transition from DRAFT to PENDING_CONSENT
```

Change it to handle three states:

```python
if agreement.status == AgreementStatus.PENDING_CONSENT:
    if ConsentSelector.all_parties_consented(agreement_id=agreement_id):
        raise DomainError(
            "All parties have already consented. Proceed to seal."
        )
    ConsentRecord.objects.filter(agreement=agreement).delete()
elif agreement.status in (AgreementStatus.DRAFT, AgreementStatus.ACTIVE):
    agreement.status = next_state(agreement.status, "request_consent")
    agreement.save(update_fields=["status", "updated_at"])
    event_type = (
        "agreement.reseal_consent_requested"
        if agreement.status == AgreementStatus.PENDING_CONSENT and original_status == AgreementStatus.ACTIVE
        else "agreement.consent_requested"
    )
    AuditService.record_event(
        event_type=event_type,
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
```

Actually, this needs care. Let me simplify: save the original status, then use it for the audit event:

In `request_otp`, after the `can_request_consent` check and before the status check, add:

```python
original_status = agreement.status
```

Then replace the `if/else` block with:

```python
if agreement.status == AgreementStatus.PENDING_CONSENT:
    if ConsentSelector.all_parties_consented(agreement_id=agreement_id):
        raise DomainError(
            "All parties have already consented. Proceed to seal."
        )
    ConsentRecord.objects.filter(agreement=agreement).delete()
else:
    agreement.status = next_state(agreement.status, "request_consent")
    agreement.save(update_fields=["status", "updated_at"])
    event_type = (
        "agreement.reseal_consent_requested"
        if original_status == AgreementStatus.ACTIVE
        else "agreement.consent_requested"
    )
    AuditService.record_event(
        event_type=event_type,
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
```

- [ ] **Step 2: Run consent tests**

Run: `cd kotoku-backend && python -m pytest apps/consent/tests/ -v`
Expected: All PASS

- [ ] **Step 3: Add test for reseal consent flow**

Add to `apps/agreements/tests/test_edit_reseal.py`:

```python
class TestResealConsentFlow:
    def test_active_can_transition_to_pending_consent(self, db):
        agreement = _make_sealed_agreement()
        agreement.status = AgreementStatus.ACTIVE
        agreement.sealed_at = None
        agreement.seal_hash = ""
        agreement.save()
        from apps.agreements.domain.policies import can_request_consent
        assert can_request_consent(agreement) is True

    def test_request_consent_from_active_goes_to_pending(self, db):
        from apps.consent.services import ConsentService
        account = _account("reseal_otp@test.com")
        agreement = AgreementService.create_draft(
            title="Re-Seal Test", created_by=account
        )
        id1 = _identity(account, "ref-r1")
        id2 = IdentityRecord.objects.create(
            account=account, reference="ref-r2", verification_type="phone"
        )
        Party.objects.create(
            agreement=agreement, identity=id1, role="buyer", display_name="Buyer"
        )
        Party.objects.create(
            agreement=agreement, identity=id2, role="seller", display_name="Seller"
        )
        agreement.status = AgreementStatus.ACTIVE
        agreement.sealed_at = None
        agreement.seal_hash = ""
        agreement.save()
        records = ConsentService.request_otp(agreement_id=agreement.pk)
        assert len(records) == 2
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT
```

- [ ] **Step 4: Run the new tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_edit_reseal.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add apps/consent/services.py apps/agreements/tests/test_edit_reseal.py
git commit -m "feat: extend consent service for re-seal OTP flow from ACTIVE"
```

---

### Task 7: Update consent flow verify to handle reseal seal path

**Files:**
- Modify: `apps/consent/services.py` — `verify_otp` method

The `verify_otp` method currently transitions to ACTIVE via `all_consented` when all parties consent from PENDING_CONSENT. For the reseal flow, after all parties consent from PENDING_CONSENT (which came from ACTIVE), we want them to be in PENDING_CONSENT status — they should then use the seal endpoint. Verify that the `all_consented` transition from PENDING_CONSENT → ACTIVE won't cause issues for reseal.

Read the `verify_otp` method. It transitions via `next_state(agreement.status, "all_consented")` which is `PENDING_CONSENT → ACTIVE`. For reseal, we want the agreement to stay in PENDING_CONSENT so the seal endpoint can be called. The seal endpoint transitions `PENDING_CONSENT → SEALED` via the `seal` action.

**Resolution:** The `all_consented` auto-transition would move us back to ACTIVE, which isn't what we want for re-seal. We need to change this: after all consent from a PENDING_CONSENT that originated from ACTIVE, we should stay in PENDING_CONSENT (ready for seal).

**Better approach:** Remove the auto-transition to ACTIVE in `verify_otp`. The agreement should stay in PENDING_CONSENT until the user explicitly seals. The Sprint 6 fast path is `PENDING_CONSENT → seal → SEALED`, so `all_consented` auto-transition is only useful for the legacy flow. We can keep it for backward compatibility but skip it if the agreement was previously sealed (has a revision).

- [ ] **Step 1: Modify `verify_otp` to skip auto-transition for reseal**

In `apps/consent/services.py`, in the `verify_otp` method, after line `all_granted = not ConsentRecord.objects.filter(...)`, change the transition logic:

Currently:
```python
if all_granted:
    new_status = next_state(agreement.status, "all_consented")
    agreement.status = new_status
    agreement.save(update_fields=["status", "updated_at"])
    AuditService.record_event(
        event_type="agreement.all_consented",
        entity_type="agreement",
        entity_id=str(agreement.pk),
    )
```

Change to:
```python
if all_granted:
    has_revision = AgreementRevision.objects.filter(
        agreement=agreement
    ).exists()
    if not has_revision:
        new_status = next_state(agreement.status, "all_consented")
        agreement.status = new_status
        agreement.save(update_fields=["status", "updated_at"])
        AuditService.record_event(
            event_type="agreement.all_consented",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
    else:
        AuditService.record_event(
            event_type="agreement.reseal_all_consented",
            entity_type="agreement",
            entity_id=str(agreement.pk),
        )
```

Add import at top of file:
```python
from apps.agreements.models import AgreementRevision
```

- [ ] **Step 2: Write test for reseal consent-then-seal flow**

Add to `apps/agreements/tests/test_edit_reseal.py`:

```python
class TestResealSealFlow:
    def test_reseal_seal_after_consent(self, db):
        agreement = _make_sealed_agreement()

        # Reopen
        agreement.status = AgreementStatus.REOPEN_REQUESTED
        agreement.save()
        AgreementService.complete_bilateral_reopen(agreement_id=agreement.pk)

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.ACTIVE

        # Edit (simplified)
        AgreementService.update_active(
            agreement_id=agreement.pk, title="Updated Title"
        )

        # Request re-seal consent
        agreement.refresh_from_db()
        from apps.consent.services import ConsentService
        records = ConsentService.request_otp(agreement_id=agreement.pk)
        assert len(records) == 2

        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

        # Confirm both parties
        from apps.consent.services import hash_otp, generate_otp_expiry
        for record in records:
            record.granted = True
            record.granted_at = timezone.now()
            record.save(update_fields=["granted", "granted_at"])

        # Verify does NOT auto-transition to ACTIVE (re-seal path)
        # Instead stays PENDING_CONSENT for seal
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatus.PENDING_CONSENT

        # Seal
        sealed = AgreementService.seal_agreement(agreement_id=agreement.pk)
        assert sealed.status == AgreementStatus.SEALED
        assert sealed.sealed_at is not None
        assert sealed.seal_hash != ""
```

- [ ] **Step 3: Run all tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_edit_reseal.py apps/consent/tests/test_consent.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add apps/consent/services.py apps/agreements/tests/test_edit_reseal.py
git commit -m "feat: skip auto-transition for reseal consent, stay in PENDING_CONSENT for seal"
```

---

### Task 8: Add AgreementRevisionSerializer and run full backend migration

**Files:**
- Modify: `apps/agreements/api/serializers.py`
- Run migration

- [ ] **Step 1: Add AgreementRevisionSerializer**

In `apps/agreements/api/serializers.py`, add:

```python
class AgreementRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgreementRevision
        fields = ("id", "revision_number", "seal_hash", "sealed_at", "created_at")
```

Add import at top:
```python
from apps.agreements.models import Agreement, AgreementRevision, Annotation
```

- [ ] **Step 2: Run the migration**

Run: `cd kotoku-backend && python manage.py migrate`
Expected: Migration 0004 applied successfully

- [ ] **Step 3: Run complete backend test suite**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/ apps/consent/tests/ apps/parties/tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add apps/agreements/api/serializers.py
git commit -m "feat: add AgreementRevisionSerializer"
```

---

### Task 9: Frontend — Add "active" to agreement status type and isReopened to store

**Files:**
- Modify: `src/types/agreement.ts`
- Modify: `src/features/agreements/agreementStore.ts`

- [ ] **Step 1: Add "active" to AgreementStatus type**

In `src/types/agreement.ts`, add `"active"` to the `AgreementStatus` union type:

```typescript
export type AgreementStatus =
  | "draft"
  | "awaiting_other_party"
  | "ready_for_review"
  | "ready_to_seal"
  | "active"
  | "sealed"
  | "reopen_requested"
  | "reopened_mutual"
  | "pending_consent"
  | "superseded"
  | "annotated_post_seal"
  | "archived"
  | "expired";
```

- [ ] **Step 2: Add isReopened flag to agreementStore**

In `src/features/agreements/agreementStore.ts`, add to the `AgreementDraftStore` interface after the `consentB` field:

```typescript
isReopened: boolean;
```

Add to the store state after `consentB`:

```typescript
isReopened: false,
```

Add action:

```typescript
setIsReopened: (v: boolean) => set({ isReopened: v }),
```

Update `reset` to include:

```typescript
reset: () =>
  set({
    agreementId: null,
    scenarioId: null,
    stepIndex: 0,
    partyA: emptyParty,
    partyB: emptyParty,
    subjectData: {},
    consentA: emptyConsent,
    consentB: emptyConsent,
    isReopened: false,
  }),
```

- [ ] **Step 3: Commit**

```bash
git add src/types/agreement.ts src/features/agreements/agreementStore.ts
git commit -m "feat: add active status type and isReopened flag to agreement store"
```

---

### Task 10: Frontend — Add "Edit agreement" button on vault detail

**Files:**
- Modify: `app/(main)/vault/[agreementId].tsx`

- [ ] **Step 1: Add edit button for active agreements**

In `app/(main)/vault/[agreementId].tsx`, add import for router and Button:

At the top, add to imports:
```typescript
import { Button } from "@/components/ui";
```

After the "Seal details" section and before the `<ReopenSection>`, add the edit button:

```tsx
{record.agreementStatus === "active" && (
  <View className="gap-sm">
    <Button
      title="Edit agreement"
      variant="primary"
      size="lg"
      fullWidth
      onPress={() => {
        router.push(`/agreement/${record.agreementId}/steps/parties?reopened=1`);
      }}
    />
    <Text className="text-xs text-ink-muted text-center">
      This agreement has been reopened for editing. Make your changes and re-seal.
    </Text>
  </View>
)}
```

- [ ] **Step 2: Commit**

```bash
git add "app/(main)/vault/[agreementId].tsx"
git commit -m "feat: add Edit agreement button on vault detail for active agreements"
```

---

### Task 11: Frontend — Step flow re-edit mode (banner, labels)

**Files:**
- Modify: `app/agreement/[id]/steps/_layout.tsx`
- Modify: `app/agreement/[id]/steps/consent.tsx`

- [ ] **Step 1: Read `reopened` query param and set store flag in step layout**

In `app/agreement/[id]/steps/_layout.tsx`, add:

```typescript
import { useLocalSearchParams, useRouter } from "expo-router";
```

(It's already imported). Add `useEffect` import and `useAgreementStore`:

```typescript
import { useEffect } from "react";
```

In the `StepsLayout` component, read the `reopened` param and set the store:

```typescript
const { id, reopened } = useLocalSearchParams<{ id: string; reopened?: string }>();
const setIsReopened = useAgreementStore((s) => s.setIsReopened);

useEffect(() => {
  if (reopened === "1") {
    setIsReopened(true);
  }
}, [reopened]);
```

Add a banner when `isReopened` is true:

```typescript
const isReopened = useAgreementStore((s) => s.isReopened);
```

In the return, before the `Stack` component, or as a header component, add a conditional banner. Since this is a Stack layout, modify the header to show a re-edit banner:

After the `STEPS` import and before `export default function StepsLayout()`, we need to add the banner inside the layout. The cleanest approach is to add it as a view above the Stack:

```tsx
return (
  <>
    {isReopened && (
      <View className="bg-amber-50 px-lg py-sm border-b border-amber-200">
        <Text className="text-sm font-medium text-amber-700 text-center">
          Re-editing agreement — Make changes and re-seal
        </Text>
      </View>
    )}
    <Stack screenOptions={{ headerShown: false }}>
      {/* ...existing screens... */}
    </Stack>
  </>
);
```

- [ ] **Step 2: Update consent step labels for reseal**

In `app/agreement/[id]/steps/consent.tsx`, get `isReopened` from store:

```typescript
const isReopened = useAgreementStore((s) => s.isReopened);
```

Change the title from `"Confirm consent"` to a conditional:

```tsx
<Text className="text-xl font-semibold text-ink-primary">
  {isReopened ? "Re-seal agreement" : "Confirm consent"}
</Text>
```

Change the description:

```tsx
<Text className="text-md text-ink-secondary">
  {isReopened
    ? "Both parties must confirm with a one-time code before the agreement can be re-sealed."
    : "Both parties must confirm with a one-time code before the agreement can be sealed."}
</Text>
```

Change the seal button text:

```tsx
<Button
  title={isReopened ? "Re-seal agreement" : "Seal agreement"}
  variant="primary"
  size="lg"
  loading={sealMutation.isPending}
  onPress={() => sealMutation.mutate()}
/>
```

- [ ] **Step 3: Commit**

```bash
git add app/agreement/[id]/steps/_layout.tsx app/agreement/[id]/steps/consent.tsx
git commit -m "feat: re-edit banner and re-seal labels in step flow"
```

---

### Task 12: Frontend — Update sealed screen for reseal

**Files:**
- Modify: `app/agreement/[id]/sealed.tsx`

- [ ] **Step 1: Read sealed.tsx and add reseal messaging**

Read the current `sealed.tsx` file.

In `sealed.tsx`, add `isReopened` from the store:

```typescript
import { useAgreementStore } from "@/features/agreements/agreementStore";
```

In the component:

```typescript
const isReopened = useAgreementStore((s) => s.isReopened);
```

Change the success title/message:

```tsx
<Text className="text-xl font-semibold text-ink-primary">
  {isReopened ? "Agreement re-sealed" : "Agreement sealed"}
</Text>
<Text className="text-md text-ink-secondary">
  {isReopened
    ? "Your agreement has been updated and re-sealed."
    : "Your agreement has been sealed and is now legally binding."}
</Text>
```

- [ ] **Step 2: Commit**

```bash
git add app/agreement/[id]/sealed.tsx
git commit -m "feat: re-sealed messaging on sealed screen"
```

---

### Task 13: Frontend — Populate agreement data when entering re-edit mode

**Files:**
- Modify: `src/features/agreements/useAgreementDraft.ts`

- [ ] **Step 1: Add useReactivateDraft hook**

In `src/features/agreements/useAgreementDraft.ts`, add a hook that populates the agreement store from existing agreement data when re-entering in re-edit mode:

```typescript
export function useReactivateDraft(id: number) {
  const { data: agreement } = useAgreement(id);
  const setPartyA = useAgreementStore((s) => s.setPartyA);
  const setPartyB = useAgreementStore((s) => s.setPartyB);
  const setSubjectData = useAgreementStore((s) => s.setSubjectData);
  const initDraft = useAgreementStore((s) => s.initDraft);
  const isReopened = useAgreementStore((s) => s.isReopened);

  useEffect(() => {
    if (!agreement || !isReopened) return;
    initDraft(agreement.id, agreement.scenarioId as ScenarioId);
    if (agreement.parties && agreement.parties.length >= 1) {
      setPartyA({
        fullName: agreement.parties[0].displayName,
        phone: agreement.parties[0].phone || "",
        idType: (agreement.parties[0].idType as IdType) || "ghana_card",
        idNumber: agreement.parties[0].idNumber || "",
      });
    }
    if (agreement.parties && agreement.parties.length >= 2) {
      setPartyB({
        fullName: agreement.parties[1].displayName,
        phone: agreement.parties[1].phone || "",
        idType: (agreement.parties[1].idType as IdType) || "ghana_card",
        idNumber: agreement.parties[1].idNumber || "",
      });
    }
  }, [agreement, isReopened, initDraft, setPartyA, setPartyB, setSubjectData]);
}
```

Add the necessary imports at the top:

```typescript
import { useEffect } from "react";
import type { IdType } from "./agreementStore";
```

- [ ] **Step 2: Use the hook in the parties step**

In `app/agreement/[id]/steps/parties.tsx`, add the hook call:

```typescript
import { useReactivateDraft } from "@/features/agreements/useAgreementDraft";

export default function PartiesStep() {
  const { id } = useLocalSearchParams<{ id: string }>();
  useReactivateDraft(Number(id));
  // ... rest of component
}
```

- [ ] **Step 3: Commit**

```bash
git add src/features/agreements/useAgreementDraft.ts app/agreement/[id]/steps/parties.tsx
git commit -m "feat: populate agreement store from existing data in re-edit mode"
```

---

### Task 14: Run full test suite and verify migration

- [ ] **Step 1: Run full backend test suite**

Run: `cd kotoku-backend && python -m pytest apps/ -v --tb=short`
Expected: All PASS

- [ ] **Step 2: Run Django checks**

Run: `cd kotoku-backend && python manage.py check`
Expected: No issues

- [ ] **Step 3: Verify migration applies cleanly**

Run: `cd kotoku-backend && python manage.py migrate --run-syncdb`
Expected: All migrations applied

- [ ] **Step 4: Final commit with any remaining fixes**

```bash
git add -A
git commit -m "feat: edit-and-reseal flow complete — backend + frontend"
```