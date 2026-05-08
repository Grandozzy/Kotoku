# Drafts Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix stale drafts on home screen — sealed agreements should not appear in drafts list, and old drafts should be auto-deleted after 30 days.

**Architecture:** Three-pronged fix: (1) verify seal updates status correctly, (2) add Celery task to delete stale drafts, (3) add frontend refetch on focus for fresh data.

**Tech Stack:** Django, Celery, React Query (TanStack Query)

---

## File Structure

| File | Action |
|------|--------|
| `apps/agreements/tasks.py` | Create — cleanup task |
| `config/settings/base.py` | Modify — add beat schedule entry |
| `src/features/agreements/usePendingActions.ts` | Modify — add refetch options |
| `apps/agreements/services.py` | Verify (may not need changes) |

---

### Task 1: Create Draft Cleanup Task

**Files:**
- Create: `kotoku-backend/apps/agreements/tasks.py`
- Test: `kotoku-backend/apps/agreements/tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

```python
# kotoku-backend/apps/agreements/tests/test_tasks.py
from datetime import timedelta
from django.utils import timezone
from apps.agreements.models import Agreement
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.tasks import cleanup_stale_drafts

def test_cleanup_deletes_old_drafts(db):
    # Create draft older than 30 days
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(username="testuser", password="testpass123")
    old_draft = Agreement.objects.create(
        title="Old Draft",
        status=AgreementStatus.DRAFT,
        created_by=user.account
    )
    old_draft.updated_at = timezone.now() - timedelta(days=31)
    old_draft.save()

    # Create recent draft (should NOT be deleted)
    recent_draft = Agreement.objects.create(
        title="Recent Draft",
        status=AgreementStatus.DRAFT,
        created_by=user.account
    )

    result = cleanup_stale_drafts()

    assert result["deleted"] == 1
    assert Agreement.objects.filter(id=old_draft.id).exists() is False
    assert Agreement.objects.filter(id=recent_draft.id).exists() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_tasks.py::test_cleanup_deletes_old_drafts -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'apps.agreements.tasks'"

- [ ] **Step 3: Write minimal implementation**

```python
# kotoku-backend/apps/agreements/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.agreements.models import Agreement
from apps.agreements.domain.enums import AgreementStatus


@shared_task
def cleanup_stale_drafts() -> dict:
    """Delete drafts older than 30 days."""
    cutoff = timezone.now() - timedelta(days=30)
    
    deleted_count, _ = Agreement.objects.filter(
        status=AgreementStatus.DRAFT,
        updated_at__lt=cutoff
    ).delete()
    
    return {"deleted": deleted_count}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_tasks.py::test_cleanup_deletes_old_drafts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kotoku-backend/apps/agreements/tasks.py kotoku-backend/apps/agreements/tests/test_tasks.py
git commit -m "feat: add cleanup_stale_drafts task to delete old drafts"
```

---

### Task 2: Register Celery Beat Schedule

**Files:**
- Modify: `kotoku-backend/config/settings/base.py:108-113`

- [ ] **Step 1: Add beat schedule entry**

```python
# In CELERY_BEAT_SCHEDULE dict, add:
"cleanup-stale-drafts": {
    "task": "apps.agreements.tasks.cleanup_stale_drafts",
    "schedule": 86400,  # once per day (seconds)
},
```

- [ ] **Step 2: Verify no syntax errors**

Run: `cd kotoku-backend && python -c "from config.settings.base import CELERY_BEAT_SCHEDULE; print('cleanup-stale-drafts' in CELERY_BEAT_SCHEDULE)"`
Expected: True

- [ ] **Step 3: Commit**

```bash
git add kotoku-backend/config/settings/base.py
git commit -m "chore: add cleanup-stale-drafts to Celery beat schedule"
```

---

### Task 3: Add Frontend Refetch on Focus

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts`

- [ ] **Step 1: Add refetch options**

```typescript
// Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts
export function usePendingActions() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  return useQuery({
    queryKey: ["pending-actions"],
    queryFn: fetchPendingActions,
    enabled: isAuthenticated,
    refetchOnFocus: true,
    staleTime: 30000,
  });
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd Kotoku-frontend/kotoku-mobile && npx tsc --noEmit`
Expected: No errors related to usePendingActions

- [ ] **Step 3: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts
git commit -m "feat: add refetchOnFocus and staleTime to usePendingActions"
```

---

### Task 4: Verify Seal Flow (Optional - May Already Work)

**Files:**
- Modify: `kotoku-backend/apps/agreements/services.py` (if needed)
- Test: `kotoku-backend/apps/agreements/tests/test_services.py`

- [ ] **Step 1: Write test to verify seal status transition**

```python
def test_seal_transitions_draft_to_sealed(db):
    from django.contrib.auth import get_user_model
    from apps.agreements.models import Agreement, Party
    from apps.agreements.domain.enums import AgreementStatus
    from apps.agreements.services import AgreementService

    User = get_user_model()
    user = User.objects.create_user(username="testuser2", password="testpass123")
    
    agreement = Agreement.objects.create(
        title="Test Agreement",
        status=AgreementStatus.DRAFT,
        created_by=user.account
    )
    # Add parties required for seal
    Party.objects.create(agreement=agreement, role="buyer", full_name="Buyer", phone="+233501111111")
    Party.objects.create(agreement=agreement, role="seller", full_name="Seller", phone="+233502222222")
    # Add consent records
    from apps.consent.models import ConsentRecord
    for party in agreement.parties.all():
        ConsentRecord.objects.create(
            agreement=agreement,
            party=party,
            purpose=ConsentRecord.Purpose.CONSENT,
            granted=True,
            expires_at=timezone.now() + timedelta(minutes=10)
        )

    sealed_agreement = AgreementService.seal_agreement(agreement_id=agreement.id)

    assert sealed_agreement.status == AgreementStatus.SEALED
```

- [ ] **Step 2: Run test**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_services.py::test_seal_transitions_draft_to_sealed -v`

- [ ] **Step 3: If PASS, skip to commit. If FAIL, investigate and fix.**

- [ ] **Step 4: Commit (if changes made)**

```bash
git add kotoku-backend/apps/agreements/services.py
git commit -m "fix: ensure seal_agreement updates status from DRAFT to SEALED"
```

---

### Task 5: Final Verification

**Files:**
- All files from above

- [ ] **Step 1: Run all tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/ -v`
Expected: All pass

- [ ] **Step 2: Run frontend TypeScript check**

Run: `cd Kotoku-frontend/kotoku-mobile && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Push all commits**

```bash
git push
```

---

## Summary

| Task | Files | Time |
|------|-------|------|
| 1. Cleanup task | tasks.py, test_tasks.py | ~15 min |
| 2. Beat schedule | settings/base.py | ~5 min |
| 3. Frontend refresh | usePendingActions.ts | ~5 min |
| 4. Verify seal | services.py (if needed) | ~10 min |
| 5. Final verification | all | ~5 min |
| **Total** | | **~40 min** |