# Reopen Discovery & Home Screen Pending Actions

**Date:** 2026-05-07
**Status:** Approved
**Branch:** `feat/bilateral-reopen-e2e-test`

## Problem

The bilateral reopen flow is broken for two reasons:

1. **Counterparties (Bob) cannot see agreements.** Both `GET /api/agreements/` and `GET /api/vault/` filter by `created_by`, so a party who didn't create the agreement sees zero entries. Bob has no way to discover a reopen request.

2. **Status is invisible at list level.** The vault card shows "Sealed" for everything, including `reopen_requested`. The home screen is static with no data fetching.

3. **ReopenSection doesn't use API response.** After confirming OTP, the UI shows "Waiting for other party..." forever because it ignores the response that tells it the current status.

## Design

### Layer 1: Backend — Counterparty Access

Extend agreement and vault selectors to include agreements where the user's phone matches a Party on the agreement.

**`AgreementSelector.list_agreements`:**
```python
qs = qs.filter(
    models.Q(created_by_id=account_id) |
    models.Q(parties__phone=request_user_phone)
).distinct()
```

**`VaultSelector.list_for_account` and `get_for_agreement`:**
Same pattern — add OR clause for `agreement__parties__phone`.

**New endpoint: `GET /api/agreements/pending-actions/`**

Returns agreements where the user needs to take action:
- `draft` where user is creator
- `pending_consent` where user hasn't consented yet
- `reopen_requested` where user hasn't confirmed reopen yet

Response shape:
```json
{
  "status": "ok",
  "data": {
    "action_required": [...agreements needing OTP/action...],
    "drafts": [...user's draft agreements...]
  }
}
```

Each agreement item includes: `id`, `title`, `status`, `scenario_template`, `pending_action` (string describing what's needed, e.g. "Enter your reopen code" or "Enter your consent code"), `created_at`, `updated_at`.

### Layer 2: Home Screen — Pending Actions

Replace static home screen with data-driven layout:

```
┌─────────────────────────────┐
│  [New agreement]  (button)  │
├─────────────────────────────┤
│  Action required            │  ← amber/warning header
│  ┌─────────────────────────┐│
│  │ Toyota Corolla Sale     ││  ← reopen_requested
│  │ Reopen requested        ││
│  │ Tap to enter code →     ││
│  └─────────────────────────┘│
│  ┌─────────────────────────┐│
│  │ Land Lease Agreement    ││  ← pending_consent
│  │ Pending your consent    ││
│  │ Tap to enter code →     ││
│  └─────────────────────────┘│
├─────────────────────────────┤
│  Drafts                     │
│  ┌─────────────────────────┐│
│  │ Used vehicle sale       ││  ← draft
│  │ Last edited 2m ago      ││
│  │ Continue →              ││
│  └─────────────────────────┘│
├─────────────────────────────┤
│  Recent agreements          │
│  (last 3-5 of any status)   │
└─────────────────────────────┘
```

**Navigation:**
- `reopen_requested` → vault detail (where ReopenSection with OTP lives)
- `pending_consent` → agreement detail (where consent OTP lives)
- `draft` → agreement editor

**Empty states:** If a section has no items, don't show the section header at all.

**Pull-to-refresh** on the whole ScrollView.

### Layer 3: Vault List — Status Badges

Update `VaultCard` to use `agreementStatus` for badges:

| agreementStatus | Badge label | Badge variant | Visual cue |
|---|---|---|---|
| `sealed` | "Sealed" | `sealed` (blue) | Normal |
| `reopen_requested` | "Reopen Requested" | `default` (amber) | Amber left border |
| `active` | "Active" | `sealed` (green) | Normal |
| `expired` | "Expired" | `default` (gray) | Normal |

The vault list API already returns `agreement.status` in the nested object. Update `mapVaultRecord` in `src/api/vault.ts` to map `agreementStatus` from `raw.agreement.status`.

### Layer 4: Fix ReopenSection

**Use API response for immediate state update:**

`confirmReopenOtp` returns `{ granted: bool, agreement_status: string }`. After calling it:
- If `agreement_status === "active"` → show success ("Agreement reopened!") then navigate to vault list after 2 seconds
- If `agreement_status === "reopen_requested"` → show "You confirmed. Waiting for other party..."

**Creator-only request button:**

"Request Reopen" only shows when the current user is the agreement creator. Add `createdByPhone` to the vault record response so the mobile app can compare with `useSessionStore().phone`.

## Files Changed

### Backend
- `apps/agreements/selectors.py` — extend filters for counterparty access
- `apps/vault/selectors.py` — extend filters for counterparty access
- `apps/agreements/api/views.py` — add `PendingActionsView`
- `apps/agreements/api/urls.py` — add pending-actions route
- `apps/vault/api/serializers.py` — add `created_by_phone` to vault response

### Mobile
- `src/api/agreements.ts` — add `fetchPendingActions`
- `src/features/agreements/usePendingActions.ts` — new hook
- `src/components/agreement/AgreementCard.tsx` — use for home screen cards
- `app/(main)/home.tsx` — replace static content with data-driven layout
- `src/components/vault/VaultCard.tsx` — use `agreementStatus` for badge
- `src/components/vault/ReopenSection.tsx` — use API response, creator check
- `src/types/vault.ts` — add `createdByPhone` field

## Out of Scope
- Push notifications (future phase)
- In-app notification center
- Real-time/polling on vault detail
- Deep linking from SMS
