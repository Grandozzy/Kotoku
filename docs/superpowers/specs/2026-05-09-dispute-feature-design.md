# Dispute Feature Design

## Overview

Enable parties to raise disputes on sealed agreements and generate case packs for dispute resolution.

## Backend

### Current State
- `Dispute` model exists with: agreement FK, raised_by Party, reason, status (open/investigating/resolved/dismissed), resolution, timestamps
- API: `POST /agreements/{agreementId}/disputes` — creates dispute

### Changes

1. **Add is_sealed check**
   - Validate agreement status is `sealed` before allowing dispute creation
   - Return 400 error if agreement not sealed

2. **Add `GET /disputes/{disputeId}` endpoint**
   - Return dispute detail with agreement summary
   - Include party names, agreement type, seal date

3. **Add `POST /disputes/{disputeId}/case-pack` endpoint**
   - Generate PDF case pack with:
     - Agreement summary
     - Evidence index
     - Dispute details
     - Seal timestamp

## Frontend

### Disputes Tab (`/disputes`)
- Pull list of user's disputes from API
- Each item shows: agreement type, counterparty, status, date
- Tap to navigate to dispute detail

### Vault Detail (`/vault/[id]`)
- Add "Raise Dispute" button for sealed agreements
- Opens sheet with:
  - Agreement info (read-only)
  - Reason text area
  - Cancel/Submit buttons

### Dispute Detail (`/disputes/[id]`)
- Show: agreement summary, raised_by party, reason, status, timestamps
- Show "Generate Case Pack" button (if API exists)
- Status badge with color coding

## API Specification

```
POST /agreements/{agreementId}/disputes
  Body: { "raised_by_party_id": int, "reason": string }
  Response: { "dispute": { ... } }
  Errors: 400 if not sealed

GET /disputes/{disputeId}
  Response: { "dispute": { agreement, raised_by, reason, status, ... } }

POST /disputes/{disputeId}/case_pack
  Response: { "download_url": string }
```

## Data Models

### DisputeSerializer
```python
{
    "id": int,
    "agreement": { "id", "type", "sealed_at", "parties": [...] },
    "raised_by": { "id", "full_name", "role" },
    "reason": string,
    "status": string,
    "resolution": string,
    "created_at": datetime,
    "resolved_at": datetime,
}
```

## Testing

- Backend: test dispute creation on sealed vs draft, status transitions
- Frontend: test flow from vault → raise dispute → disputes list → detail