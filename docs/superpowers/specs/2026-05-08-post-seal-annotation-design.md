# Post-Seal Annotation Feature — Frontend Implementation

**Date:** 2026-05-08
**Feature:** Post-seal annotation from vault detail
**Status:** Design approved, implementation pending

---

## What It Is

Allow parties to add notes (annotations) to a sealed agreement without modifying core content. Notes are append-only, timestamped, and tied to the author party.

---

## UI/UX Specification

### Locations

1. **Floating Action Button (FAB)**
   - Position: Bottom right, 16px from edges
   - Icon: Plus (+)
   - Opens bottom sheet on tap

2. **Bottom Sheet Modal**
   - Header: "Add note" with close (X) button
   - Body: TextArea, 1000 char max, multiline (4-6 lines visible)
   - Footer: "Save" button (disabled when empty)
   - Behavior: Tap outside to dismiss

3. **Activity Section**
   - "Notes" subsection in Activity section
   - Each note shows: author name, relative timestamp, body
   - Sorted oldest → newest

### Visibility

FAB/notes section shown only when:
- `agreementStatus === "sealed"` OR
- `agreementStatus === "reopen_requested"` OR
- `agreementStatus === "active"` (reopened state)

---

## API Specification

### Endpoints

```
GET /api/agreements/{agreementId}/annotations/
POST /api/agreements/{agreementId}/annotations/
```

### Request (POST)

```json
{
  "author_party_id": 123,
  "body": "Keys handed over on Monday."
}
```

### Response

```json
{
  "data": {
    "annotation": {
      "id": 1,
      "author_party_id": 123,
      "body": "Keys handed over on Monday.",
      "created_at": "2026-05-08T10:30:00Z"
    }
  }
}
```

### List Response

```json
{
  "data": {
    "annotations": [
      {
        "id": 1,
        "author_party_id": 123,
        "author": { "display_name": "Kofi", "role": "seller" },
        "body": "Keys handed over on Monday.",
        "created_at": "2026-05-08T10:30:00Z"
      }
    ]
  }
}
```

---

## Technical Implementation

### New Files

1. `src/api/annotations.ts` — API client functions
2. `src/features/annotations/useAnnotations.ts` — React Query hook
3. `src/features/annotations/useAddAnnotation.ts` — mutation hook  
4. `src/components/annotations/AnnotationSection.tsx` — notes list display
5. `src/components/annotations/AddNoteSheet.tsx` — bottom sheet modal

### Modified Files

1. `app/(main)/vault/[agreementId].tsx` — add FAB + AnnotationSection

### Data Types

```typescript
interface Annotation {
  id: number;
  authorPartyId: number;
  author: {
    displayName: string;
    role: string;
  };
  body: string;
  createdAt: string;
}

interface CreateAnnotationPayload {
  author_party_id: number;
  body: string;
}
```

### State Management

- React Query for list + cache
- Optimistic updates on create
- Invalidate after create success

---

## Acceptance Criteria

1. FAB visible on vault detail for sealed/reopen_requested/active agreements
2. Tapping FAB opens bottom sheet
3. Saving note → POST /api/agreements/{id}/annotations/
4. Success → note appears in Notes subsection in Activity
5. Notes list shows all annotations with author + timestamp
6. Empty body → Save button disabled
7. 1000 char limit enforced
8. Non-party → button hidden or 403 handled
9. Network error → show error message, allow retry

---

## Backend Reference

- `kotoku-backend/apps/agreements/annotation_services.py` — service layer
- `kotoku-backend/apps/agreements/api/annotations/views.py` — API views
- `kotoku-backend/tests/integration/test_annotation_flow.py` — integration tests (all passing)