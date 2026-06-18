# Evidence Upload Hardening Guide

Status date: 2026-06-18

This guide turns the evidence upload findings into an implementation sequence for backend, web, and mobile. It should be used together with `kotoku-backend/docs/architecture/evidence-upload-checklist.md` and `Kotoku-frontend/Frontend_Architecture_Note.md`.

## Target Flow

Kotoku agreement creation moves in this order:

1. Parties
2. Details
3. Evidence
4. Consent
5. Sealed agreement in Vault

The Evidence step is complete only when required evidence rows are confirmed by the backend, not merely selected locally or uploaded to S3. Clients may show local progress, but navigation to Consent must depend on confirmed evidence state.

## Shared Upload Contract

All clients must satisfy the same backend contract:

- Request a presigned upload with `evidence_type`, `mime_type`, `size_bytes`, and `checksum_sha256`.
- Upload exactly the same bytes that were measured for `size_bytes` and `checksum_sha256`.
- Send the same `file_key`, `evidence_type`, `mime_type`, and `checksum_sha256` to confirm.
- Treat backend verification mismatches as non-retryable for the current local file.
- Allow the user to replace a rejected file with a new file.
- Proceed to the next step only after required evidence is confirmed.

## Failure Policy

| Failure | Retry same file? | User action | Reason |
|---|---:|---|---|
| Network interruption before storage upload finishes | Yes | Retry | The file may not have reached storage. |
| Storage upload timeout | Yes | Retry | The client cannot prove completion. |
| Backend/storage temporary failure during confirm | Yes | Retry confirm or recover from evidence list | Backend state may already be confirmed. |
| Size mismatch | No | Replace file | The measured file and uploaded object disagree. |
| MIME mismatch | No | Replace file | The declared type and stored object disagree. |
| Checksum mismatch | No | Replace file | The uploaded bytes are not the requested bytes. |
| Evidence type mismatch | No | Replace file | The upload was confirmed against the wrong slot. |

## Implementation Order

### 1. Mobile Byte Contract

- [x] Stop using `Blob.arrayBuffer()` on Android React Native.
- [x] Read selected files through `expo-file-system`.
- [x] Compute SHA-256 and `size_bytes` from the same decoded bytes.
- [x] Infer MIME from file signatures when possible.
- [x] Do not fall back to `image/jpeg` for unknown bytes.
- [x] Reject storage upload timeout instead of confirming after timeout.
- [x] Mark contract mismatches as replace-only, not retry.
- [ ] Add focused unit tests for base64 decoding, MIME inference, and retry classification.

### 2. Web Upload Completion

- [x] Keep per-file upload state separate from agreement detail cache state.
- [x] Let locally confirmed rows unlock the proceed CTA while refetch catches up.
- [x] Recover from confirm response loss by checking confirmed evidence.
- [ ] Add tests for upload-button disabled state, confirm recovery, and proceed CTA visibility.

### 3. Backend Confirmation Contract

- [x] Verify storage object size, MIME, and checksum before confirmation.
- [x] Fail closed when verification is ambiguous.
- [x] Log structured verification diagnostics.
- [x] Make confirm idempotent for already-confirmed `file_key` + metadata.
- [x] Return structured error codes for mismatch classes.
- [x] Accept `evidence_id` on confirm while keeping `file_key` compatibility.

### 4. Product-State Gate

- [ ] Define one shared `isEvidenceStepComplete()` rule for web and mobile.
- [ ] Require all required evidence slots to be backend-confirmed.
- [ ] Use local confirmed uploads as an optimistic bridge only after confirm succeeds.
- [ ] Reconcile local state with `listEvidence()` on screen focus.

### 5. Observability and Support

- [ ] Log client phase transitions: `getUploadUrl`, `uploading`, `confirming`, `confirmed`, `failed`.
- [ ] Include non-secret diagnostics: agreement id, evidence type, status code, error code.
- [ ] Add Sentry breadcrumbs for failed evidence upload phases.
- [ ] Add manual QA cases for offline, timeout, retry, replace, and proceed behavior.

## Backend Error Codes To Add

The frontend should not parse English error text long-term. Add stable backend error codes:

- `evidence_upload_not_pending`
- `evidence_object_missing`
- `evidence_storage_unavailable`
- `evidence_file_size_mismatch`
- `evidence_mime_mismatch`
- `evidence_checksum_mismatch`
- `evidence_type_mismatch`
- `evidence_confirm_already_complete`

Keep the current `message` field for compatibility, and add `code` so clients can classify retry vs replace deterministically.

## Acceptance Checklist

- [ ] Android image upload confirms without `undefined is not a function`.
- [ ] Android upload timeout does not call confirm.
- [ ] Size/MIME/checksum mismatch shows Replace, not Retry.
- [ ] Web Upload All cannot hang with all rows confirmed.
- [ ] Web proceed CTA appears after required evidence confirms.
- [x] Backend confirm can be safely retried after response loss.
- [ ] Required evidence gates Consent on both web and mobile.
- [ ] Manual QA confirms Parties → Details → Evidence → Consent → Vault.
