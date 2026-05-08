## Summary

- **Reopen consent flow**: Both parties now enter OTP on the same phone (like new agreement consent)
- **Active agreements in vault**: Vault now shows active (reopened) agreements alongside sealed ones
- **Template loading fix**: Fixed scenarioId not being passed correctly when editing reopened agreements
- **Export download fix**: Fixed PDF download/share using expo-file-system/legacy API

## Changes

### Backend
- `apps/vault/selectors.py`: Added `ACTIVE` status to vault visible statuses
- `apps/vault/api/serializers.py`: Added `PartySummarySerializer` and `parties` field

### Frontend
- `ReopenSection.tsx`: Rewrote to show two OTP blocks (one per party)
- Agreement steps: Added URL param fallback for `scenarioId` to fix template loading
- `ExportButton.tsx`: Fixed download using `expo-file-system/legacy`
- Removed yellow border from vault cards (UI cleanup)

## Testing

1. Reopen sealed agreement → both parties confirm → agreement becomes active
2. Edit reopened agreement → go through parties → details → evidence → review → consent → seal
3. Download PDF from vault for both sealed and active agreements

## Notes

- DB fix: Updated agreements with empty `scenario_template` to `used_vehicle_sale`
- Hooks race fix: Delayed store reset after seal to prevent "Rendered fewer hooks" error

---
**Reviewers**: @Grandozzy
**Labels**: feature, backend, frontend