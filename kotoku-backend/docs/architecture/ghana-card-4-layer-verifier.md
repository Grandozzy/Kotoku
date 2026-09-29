# Ghana Card 4-Layer Verifier

Purpose: define the production identity-verification path for non-witness parties, document the decisions already made, and provide the implementation and setup checklist for rollout.

This file supersedes the narrower front/back-only enforcement plan where the two conflict.

## Summary

Non-witness parties must not be treated as identity-complete merely because files were uploaded.

Identity completion must depend on a backend-verified result across four layers:

1. Document presence and Ghana Card marker checks
2. OCR extraction and field matching
3. Selfie-to-card face comparison
4. Fraud/risk review and manual-review fallback

Current implementation status:

- Layer 1: implemented
- Layer 2: implemented
- Layer 3: implemented
- Layer 4: implemented for configured score-band review

The system can fail, pass, or route to `manual_review_required` for the configured score bands. Authorized Django administrators can inspect short-lived image links and approve or reject only eligible liveness or face-match reviews. Cross-agreement duplicate-image and advanced tamper heuristics remain future controls.

## Locked Decisions

- Non-witness parties must use `ghana_card` only.
- Ghana Card PIN in `id_number` must be unique within the agreement.
- Identity uploads remain on the existing direct-to-S3 upload contract.
- Reserved identity evidence slots are additive and role-bound.
- Identity step completion must depend on backend-confirmed verification state, not optimistic UI state.
- Selfie capture is required for non-witness parties.
- Mobile identity acquisition must support both in-app camera capture and gallery selection.
- Web identity acquisition remains file-upload based in this phase.
- Ghana Card front/back should prefer camera capture on mobile, but must not be camera-only.
- Camera capture is not equivalent to liveness detection and must not be described as such.
- Sealing must fail closed if identity verification is not `verified`.
- Ambiguous face-match results must not auto-pass.

## Identity Evidence Model

Reserved evidence slots:

- `buyer_ghana_card_front`
- `buyer_ghana_card_back`
- `buyer_selfie`
- `seller_ghana_card_front`
- `seller_ghana_card_back`
- `seller_selfie`
- `landlord_ghana_card_front`
- `landlord_ghana_card_back`
- `landlord_selfie`
- `tenant_ghana_card_front`
- `tenant_ghana_card_back`
- `tenant_selfie`

Rules:

- Ghana Card slots must be image uploads only.
- Selfie slots must be image uploads only.
- Reserved slots must match an actual party role on the agreement.
- Latest confirmed evidence per reserved slot is the current source of truth.
- Mobile clients should offer:
  - `Take photo`
  - `Choose from gallery`
- Users should be able to review and replace identity images before final upload confirmation.
- Mobile camera capture uses an ID-1 aspect-ratio guide and rejects captures below the configured minimum resolution.
- Backend verification rejects invalid, very low-resolution, extremely blurred, dark, or overexposed card images before OCR.

## Verification State Model

Each non-witness party has a `PartyIdentityVerification` record.

Status values:

- `pending`
- `processing`
- `verified`
- `failed`
- `manual_review_required`

Stored structured outputs:

- entered PIN
- entered full name
- OCR PIN
- OCR full name
- linked evidence ids for front, back, and selfie
- face match score
- failure codes
- user-safe detail message

Do not persist raw OCR text unless there is a documented compliance need.

## The 4 Layers

### Layer 1. Document Presence and Ghana Card Markers

Goal: reject obvious non-card uploads and incomplete identity bundles.

Required checks:

- front image confirmed
- back image confirmed
- selfie image confirmed
- OCR text contains Ghana Card markers on card images

Current marker strategy:

- `GHANA`
- identity-card markers such as:
  - `NATIONAL IDENTITY CARD`
  - `NATIONAL IDENTIFICATION`
  - `IDENTIFICATION AUTHORITY`
  - `IDENTITY CARD`

Failure outcome:

- missing front or back: validation error
- missing selfie: validation error
- missing Ghana Card markers: verification `failed`

### Layer 2. OCR and Field Matching

Goal: ensure the uploaded document text matches the entered identity details.

Required checks:

- OCR PIN must be extracted from front or back text
- OCR PIN must match entered PIN exactly after normalization
- entered full name tokens must match OCR text on the front image

Failure outcome:

- no OCR PIN found: `failed`
- OCR PIN mismatch: `failed`
- OCR name mismatch: `failed`

### Layer 3. Selfie-to-Card Face Comparison

Goal: confirm that the selfie photo and the Ghana Card portrait are plausibly the same person.

Current provider path:

- source image: selfie photo
- target image: Ghana Card front image
- service: AWS Rekognition `CompareFaces`

Current decision thresholds:

- similarity `< 80`: `failed`
- similarity `80-89.99`: `manual_review_required` if OCR otherwise passes
- similarity `>= 90`: eligible to pass if OCR also passes

Additional checks:

- if no usable source face is detected in the selfie, fail

Face comparison is separate from the preceding AWS Face Liveness check. Liveness verifies presence; `CompareFaces` verifies that the live reference image plausibly matches the Ghana Card portrait.

### Layer 4. Fraud / Risk / Manual Review

Goal: catch ambiguous or suspicious cases that should not auto-pass.

Current partial behavior:

- borderline face score triggers `manual_review_required`

Target full behavior:

- manual-review queue in admin or operations UI
- reason codes visible to reviewers
- reviewer decision audit log
- explicit reviewer actions:
  - approve
  - reject
  - request re-upload

Future heuristic candidates:

- repeated selfie reuse across parties or agreements
- repeated Ghana Card image reuse across parties or agreements
- very low image quality
- obvious screen recapture or print recapture patterns
- mismatch between front/back document consistency
- stronger liveness provider if adopted later

## API and Client Contract

Party payloads must expose:

- `ghana_card_front_uploaded`
- `ghana_card_back_uploaded`
- `identity_selfie_uploaded`
- `ghana_card_front_view_url`
- `ghana_card_back_view_url`
- `identity_selfie_view_url`
- `identity_verification_status`
- `identity_verification_detail`
- `identity_verification_failure_codes`

Frontend rules:

- `Proceed` on Parties step must require backend `identity_verification_status === "verified"` for all non-witness parties
- frontend must poll or refetch while status is `pending` or `processing`
- retry messaging must be explicit when status is `failed`
- `manual_review_required` must not be shown as success
- mobile should make camera capture the primary CTA for selfie upload
- mobile should offer both camera capture and gallery selection for Ghana Card front/back uploads
- identity upload guidance should explicitly warn about blur, glare, cropped edges, and unreadable text
- identity uploads must be previewable and replaceable before the user is treated as complete

## Seal Rule

`AgreementService.seal_agreement()` must not rely only on coarse `can_seal()` checks.

Required seal behavior:

- check consent
- check confirmed evidence presence
- run full `validate_agreement()`
- fail closed when any identity verification requirement is unmet

## Implementation Path

### Phase 1. Baseline Identity Enforcement

- restrict non-witness parties to `ghana_card`
- enforce PIN format and uniqueness
- add reserved front/back Ghana Card slots
- gate parties completion on backend-confirmed state

Status: complete

### Phase 2. OCR Verification

- add `PartyIdentityVerification`
- download confirmed card images from S3
- run Google Vision OCR
- match Ghana Card markers
- match OCR PIN to entered PIN
- match OCR name tokens to entered name

Status: implemented

### Phase 3. Selfie Capture and Face Match

- add selfie evidence slots
- require selfie upload in parties step
- compare selfie to card portrait with Rekognition
- add face score thresholds and manual-review band

Status: implemented

### Phase 3A. Mobile Image Acquisition Hardening

- add in-app camera capture for selfie, Ghana Card front, and Ghana Card back
- retain gallery selection fallback on mobile
- keep web on file upload
- prevent non-image file selection in client-side identity upload flows
- add pre-upload guidance and post-capture preview/replace flow

Status: pending

### Phase 4. Manual Review Operations

- admin reviewer list/filter
- approve/reject/reupload decision path
- audit log for reviewer decisions
- support-safe user messaging

Status: pending

### Phase 5. Liveness and Stronger Anti-Fraud

- AWS Rekognition Face Liveness challenge flow
- configurable pass and manual-review thresholds
- bounded retries and cooldown after repeated unsuccessful sessions
- stronger tamper and duplicate-image controls remain future work

Status: liveness implemented; additional anti-fraud controls pending

## Mobile Acquisition Decision

Decision:

- Selfie upload: primary action is in-app camera capture, with gallery fallback kept available in this phase.
- Ghana Card front/back: offer both in-app camera capture and gallery selection.
- Do not force camera-only capture in this phase.

Rationale:

- OCR and face comparison perform better when capture quality is guided at the point of acquisition.
- Forcing camera-only would create unnecessary failure modes on older devices, denied permissions, or interrupted sessions.
- Gallery fallback improves completion rates without changing the backend trust model.
- Security still depends on OCR, PIN matching, face comparison, and manual review; camera capture alone is not a fraud control.

Out of scope for image acquisition itself:

- treating camera capture as proof of liveness
- device-attestation-based identity capture

## Implementation Checklist

### Backend

- keep identity slot MIME allowlist image-only
- preserve fail-closed verification when any required identity image is missing or invalid
- keep verification detail user-safe and free of secrets or raw provider payloads

### Mobile

- add per-slot action sheet for `Take photo` / `Choose from gallery`
- use native Expo image capture and library APIs inside `src/features/`
- keep upload contract unchanged: request upload URL, upload exact bytes, confirm
- add image preview before upload confirmation
- allow replacement of failed or low-quality identity images
- keep Proceed disabled until backend verification reaches `verified`

### Web

- keep identity uploads file-based
- keep identity inputs limited to image files for reserved identity slots
- show clearer upload guidance for card readability and selfie framing

### QA

- Android: capture front/back/selfie fully in-app and confirm successful verification
- Android: choose existing gallery images and confirm fallback path works
- iPhone: repeat both camera and gallery flows
- verify permission denial still leaves gallery fallback usable
- verify blurred or obviously non-card uploads fail and require replacement
- verify web remains file-upload based and cannot upload PDFs into identity slots

## Setup Checklist

### Google Vision OCR

Google Cloud:

- [ ] Create or select the Google Cloud project
- [ ] Enable the Vision API
- [ ] Create a service account dedicated to Kotoku OCR
- [ ] Grant the service account the minimum Vision API access needed
- [ ] Generate a JSON key for the service account
- [ ] Store the JSON key securely

Backend env:

- [ ] Set `GOOGLE_VISION_SERVICE_ACCOUNT_JSON`
- [ ] Set `GOOGLE_VISION_PROJECT_ID`
- [ ] Optionally set `GOOGLE_VISION_TIMEOUT_SECONDS`

Notes:

- `GOOGLE_VISION_SERVICE_ACCOUNT_JSON` must contain the raw JSON credentials, serialized as a single env value
- do not commit the service-account JSON file to the repo

### AWS Rekognition

AWS:

- [ ] Ensure the runtime IAM principal has `rekognition:CompareFaces`
- [ ] Ensure the principal already used for S3 access is the same one intended for Rekognition, or document the split clearly
- [ ] Confirm the region supports the Rekognition operation you intend to use

Current AWS env already expected by runtime:

- [ ] `AWS_ACCESS_KEY_ID`
- [ ] `AWS_SECRET_ACCESS_KEY`
- [ ] `AWS_S3_REGION_NAME`
- [ ] `AWS_STORAGE_BUCKET_NAME`
- [ ] `AWS_SESSION_TOKEN` only if temporary credentials are used
- [ ] `AWS_REKOGNITION_LIVENESS_THRESHOLD=80`
- [ ] `AWS_REKOGNITION_LIVENESS_REVIEW_THRESHOLD=70`
- [ ] `AWS_REKOGNITION_LIVENESS_MAX_FAILURES=5`
- [ ] `AWS_REKOGNITION_LIVENESS_FAILURE_WINDOW_SECONDS=180`
- [ ] `AWS_REKOGNITION_LIVENESS_COOLDOWN_SECONDS=1800`
- [ ] `IDENTITY_LIVENESS_RETENTION_DAYS=30` on backend and worker
- [ ] `IDENTITY_CARD_MIN_SHORT_EDGE=1000`

Suggested IAM addition:

```json
{
  "Effect": "Allow",
  "Action": [
    "rekognition:CompareFaces",
    "rekognition:CreateFaceLivenessSession",
    "rekognition:GetFaceLivenessSessionResults"
  ],
  "Resource": "*"
}
```

### Celery / Worker

- [ ] Ensure worker has the same AWS env as backend
- [ ] Ensure worker has Google Vision env
- [ ] Ensure migrations are applied before worker release if model changes are included
- [ ] Confirm Celery is running and can process `apps.identity.tasks.verify_party_identity`
- [ ] Confirm Celery Beat runs `apps.identity.tasks.cleanup_expired_liveness_references` daily

### Cognito Guest Role

The browser-hosted Face Liveness component needs temporary Cognito credentials to stream the session. The unauthenticated role must not have S3, OCR, `CompareFaces`, session-result, or session-creation access.

- [ ] Set `NEXT_PUBLIC_AMPLIFY_IDENTITY_POOL_ID` in the web deployment
- [ ] Confirm the identity pool unauthenticated role permits only `rekognition:StartFaceLivenessSession`
- [ ] Restrict the policy to `eu-west-1` with `aws:RequestedRegion`
- [ ] Confirm the role has no S3 permissions
- [ ] Confirm `CreateFaceLivenessSession`, `GetFaceLivenessSessionResults`, and `CompareFaces` remain backend-only

Suggested unauthenticated-role statement:

```json
{
  "Effect": "Allow",
  "Action": "rekognition:StartFaceLivenessSession",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:RequestedRegion": "eu-west-1"
    }
  }
}
```

### Frontend

Mobile:

- [ ] Confirm camera permission prompt is present and understandable
- [ ] Confirm selfie capture uses front camera by default
- [ ] Confirm failure state allows retake

Web:

- [ ] Confirm selfie slot accepts image only
- [ ] Confirm `capture="user"` behavior is acceptable on target browsers
- [ ] Confirm fallback behavior on browsers that ignore `capture`

## Security Checklist

- [ ] Fail closed when verification is not complete
- [ ] Do not treat upload presence as verification success
- [ ] Do not store raw service-account JSON anywhere except secret storage
- [ ] Do not log uploaded image bytes
- [ ] Do not log presigned URLs, tokens, or secret provider payloads
- [ ] Do not persist raw OCR text unless explicitly required
- [ ] Use only user-safe error messages in API responses
- [ ] Keep provider retries bounded
- [ ] Keep ambiguous results out of auto-pass paths
- [ ] Require `AES256` server-side encryption on every S3 upload
- [ ] Delete Rekognition liveness references after the configured retention period
- [ ] Keep Ghana Card evidence under the agreement/evidence retention policy; do not silently delete it while the agreement requires it

## Manual QA Checklist

- [ ] Upload a real Ghana Card front and back plus selfie on mobile
- [ ] Upload a real Ghana Card front and back plus selfie on web
- [ ] Confirm parties step stays blocked while verification is `pending`
- [ ] Confirm parties step unlocks only after verification becomes `verified`
- [ ] Confirm wrong PIN causes `failed`
- [ ] Confirm non-card image causes `failed`
- [ ] Confirm missing selfie causes validation error
- [ ] Confirm borderline face score reaches `manual_review_required`
- [ ] Confirm liveness score at or above 80 proceeds to card face comparison
- [ ] Confirm liveness score from 70 through 79.99 requires manual review
- [ ] Confirm five unsuccessful checks within three minutes trigger a cooldown
- [ ] Confirm the mobile API response never exposes the raw liveness score
- [ ] Confirm sealed agreement cannot be produced when identity is not verified
- [ ] Confirm an admin can view eligible review images through expiring links and approve or reject
- [ ] Confirm review decisions create `identity.manual_review_resolved` audit events
- [ ] Confirm expired liveness references are removed from S3 and audited

## Open Gaps

- Cross-agreement duplicate-image fraud checks are not yet implemented
- Advanced document tamper detection is not yet implemented
- Ghana Card evidence retention still requires a finalized legal/product retention period

## Release Decision Rule

Beta or production rollout of this verifier is acceptable only when all are true:

- Google Vision setup is complete
- Rekognition permission is complete
- worker processing is confirmed in staging
- end-to-end QA confirms `verified`, `failed`, and `manual_review_required` flows
- support/ops knows how to handle retry and review cases
