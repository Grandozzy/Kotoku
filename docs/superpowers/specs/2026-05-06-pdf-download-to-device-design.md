# PDF Download to Device

**Date:** 2026-05-06
**Status:** Approved
**Scope:** Mobile app only — no backend changes

## Problem

The vault detail screen has a single "Share PDF" button that opens the OS share sheet (WhatsApp, email, etc.). Users want to save the PDF directly to their device's Downloads folder without going through the share sheet. The product spec (FR-12) requires a PDF export "optimized for phone sharing and printing," and the seal-success screen lists "Export/share as PDF" as a primary action.

## Decision

Add a "Save to Device" button alongside the existing "Share PDF" button. Use `expo-media-library` to save the downloaded PDF to the device Downloads folder.

## Current behavior

- `ExportButton` component downloads PDF to cache via `expo-file-system/legacy.downloadAsync`
- Opens share sheet via `expo-sharing.shareAsync`
- Single button: "Share PDF" when ready, "Preparing PDF..." when pending, "Get PDF" to request export

## New behavior

Two buttons when `pdfStatus === "ready"`:

1. **"Save to Device"** — primary button, downloads then saves to Downloads folder
2. **"Share PDF"** — secondary button, existing share sheet behavior

Both buttons share the same download-to-cache step. Only the post-download action differs.

## Data flow

### Save to Device

```
Tap "Save to Device"
  → downloadAsync(pdfUrl, cacheDir/agreement-{id}-{timestamp}.pdf)
  → MediaLibrary.createAssetAsync(localUri)
  → delete cache file
  → show toast: "Saved to Downloads"
```

### Share PDF

```
Tap "Share PDF"
  → downloadAsync(pdfUrl, cacheDir/agreement-{id}-{timestamp}.pdf)
  → Sharing.shareAsync(localUri, { mimeType: "application/pdf", dialogTitle: "Share agreement PDF" })
  → delete cache file after sharing completes
```

## Files to change

| File | Change |
|------|--------|
| `package.json` | Add `expo-media-library` dependency |
| `app.json` | Add `WRITE_EXTERNAL_STORAGE` permission for Android API < 29 |
| `src/components/vault/ExportButton.tsx` | Add `handleSaveToDevice`, restructure to two buttons, add success/error states |

## Files NOT changed

- Backend (PDF URL fix already done via `AWS_S3_EXTERNAL_URL`)
- Vault detail screen layout
- API client (`src/api/vault.ts`)
- Types (`src/types/vault.ts`)

## Error handling

| Scenario | User message |
|----------|-------------|
| Download fails | "Could not download the PDF. Please try again." |
| Storage permission denied | "Storage permission needed to save files." |
| Share fails | "Could not share the PDF. Please try again." |

## Dependencies

- `expo-media-library` — new dependency for saving to device Downloads
- `expo-file-system` — already installed, used for download
- `expo-sharing` — already installed, used for share sheet

## Out of scope

- Background download / download manager integration
- Offline caching of previously downloaded PDFs
- Download progress indicator
- Multiple file downloads (batch)
