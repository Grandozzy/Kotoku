# Drafts Cleanup & Stale Data Fix

## Problem

Home screen shows stale/duplicate drafts — agreements that were sealed still appear in drafts list. Users see items that should be gone.

## Root Cause

1. Unknown — need to verify seal flow updates status correctly
2. No cleanup mechanism — old drafts accumulate forever
3. Frontend may show cached stale data

## Solution

Three-pronged fix:

### 1. Verify Seal Flow

**File:** `apps/agreements/services.py`

**Action:** Ensure `seal_agreement()` properly transitions DRAFT → SEALED.

**Verification:** Add test to confirm status changes after seal.

### 2. Draft Cleanup Task

**New file:** `apps/agreements/tasks.py`

```python
@shared_task
def cleanup_stale_drafts():
    """Delete drafts older than 30 days."""
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count = Agreement.objects.filter(
        status=AgreementStatus.DRAFT,
        updated_at__lt=cutoff
    ).delete()
    return {"deleted": deleted_count[0]}
```

**Registration:** Add to `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`:
```python
"cleanup-stale-drafts": {
    "task": "apps.agreements.tasks.cleanup_stale_drafts",
    "schedule": 86400,  # daily
}
```

### 3. Frontend Refresh

**File:** `src/features/agreements/usePendingActions.ts`

**Change:**
```typescript
return useQuery({
  queryKey: ["pending-actions"],
  queryFn: fetchPendingActions,
  enabled: isAuthenticated,
  refetchOnFocus: true,
  staleTime: 30000,
});
```

## Files to Modify

| File | Change |
|------|--------|
| `apps/agreements/services.py` | Verify seal status update (may be OK) |
| `apps/agreements/tasks.py` | New — cleanup task |
| `config/settings/base.py` | Add beat schedule entry |
| `src/features/agreements/usePendingActions.ts` | Add refetch options |

## Acceptance Criteria

1. Sealed agreements do NOT appear in drafts list
2. Drafts older than 30 days are auto-deleted
3. Home screen shows fresh data on focus/return

## Timeline

- Verify seal: 10 min
- Cleanup task: 30 min
- Frontend refresh: 10 min
- Total: ~1 hour