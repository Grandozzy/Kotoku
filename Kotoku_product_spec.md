# Kotoku Developer-Ready Product Spec

## Product Overview

Kotoku is a mobile-first trust and evidence platform for informal and semi-formal transactions. It enables two parties to capture the state of a transaction, record agreement terms, confirm consent, and store a sealed evidence pack in a retrievable vault. Ghana's Electronic Transactions Act provides a useful legal backdrop because electronic records should not be denied admissibility solely because they are electronic, and the evidential weight of such records depends on the reliability of how they were generated, stored, and tied to the originator. [nita.gov](https://nita.gov.gh/wp-content/uploads/2017/12/Electronic-Transactions-Act-772.pdf)

The product should be built as a scenario-driven agreement engine rather than as separate applications for cars, rentals, or labor agreements. Dynamic-form architecture supports this approach because a generic client can render different questionnaires from a shared model, while the model controls the logic, conditions, and validations for each scenario. [progress](https://www.progress.com/blogs/dynamic-forms-architecture-design)

## Product Goals

### Primary goal

Enable users in low-trust transactions to create a credible, time-stamped, tamper-evident agreement pack in under five minutes on a low-end Android phone, with explicit physical participation and confirmation from both parties before sealing.

### Secondary goals

- Support multiple agreement categories through one shared UI and one shared backend workflow engine. [progress](https://www.progress.com/blogs/dynamic-forms-architecture-design)
- Reduce cognitive load with multi-step forms and progressive disclosure so users only see fields relevant to the chosen transaction type. [blog.logrocket](https://blog.logrocket.com/ux-design/progressive-disclosure-ux-types-use-cases/)
- Produce structured PDF exports that are usable in mediation, arbitration, or informal dispute resolution contexts in Ghana, where ADR remains an important parallel path to court processes. [obdickson.wordpress](https://obdickson.wordpress.com/2025/02/23/procedural-matters-in-alternative-dispute-resolution-adr-in-ghana/)

### Non-goals for v1

- Full legal-document drafting for complex commercial contracts.
- Court filing automation.
- Marketplace escrow.
- Multi-party enterprise negotiations.

## Target Users

| User segment | Typical use case | Why they use Kotoku |
|---|---|---|
| Individual buyer | Buying a used car, phone, or appliance | Needs proof of condition and terms at handover |
| Individual seller | Selling a vehicle or other high-value used asset | Wants proof of what was disclosed and accepted |
| Landlord | Renting a room or apartment | Wants proof of condition, rent terms, and deposit rules |
| Tenant | Taking possession of a room or apartment | Wants proof of initial state and agreed obligations |
| Small operator | Frequent transactions, such as small dealers or artisans | Needs reusable templates and repeatable evidence capture |

## Product Principles

1. **One app, many templates**: the app shell, components, and navigation stay stable while templates define scenario-specific questions and rules. [progress](https://www.progress.com/blogs/dynamic-forms-architecture-design)
2. **Capture first, explain later**: the system should prioritize fast evidence capture before asking for optional details.
3. **Progressive disclosure**: irrelevant fields stay hidden unless triggered by context or prior answers, which reduces form fatigue and improves mobile completion rates. [lvivity](https://lvivity.com/mobile-form-design-best-practices)
4. **Tamper-evident storage**: sealed records are append-only, and any later edit creates a new version rather than overwriting the original. Ghana's legal framework places weight on integrity and reliability of storage, making version history and auditability important product requirements. [nita.gov](https://nita.gov.gh/wp-content/uploads/2017/12/Electronic-Transactions-Act-772.pdf)
5. **Offline-resilient**: core capture should work in poor-connectivity environments and sync once a connection becomes available.
6. **Plain-language trust**: summaries and prompts should use simple language rather than legal jargon.

## Finalized Product Policies

The following policy decisions are locked for the current MVP scope and should be treated as implementation requirements rather than open questions.

| Policy area | Final decision | Implementation note |
|---|---|---|
| Dual-party confirmation | Separate OTP required for both parties before sealing | No agreement can reach `sealed` without Party A OTP and Party B OTP recorded |
| Minimum identity verification | Ghana Card + phone number + SMS OTP | Store Ghana Card image, masked identifier if needed, and phone verification timestamp |
| Export format | PDF only in v1 | Produce a human-readable PDF case pack optimized for phone sharing and printing |
| Free retention period | 2 months | After free retention, move to grace period and then locked archival unless paid |
| Editing after review | Explicit reopening only with both parties re-authenticated | Reopening requires both parties, fresh OTPs, and linked re-consent event |
| If one party is unavailable after sealing | No edit allowed; annotation or dispute note allowed instead | Preserve original sealed record and add post-seal note as a separate event |

## Core Information Architecture

The top-level information architecture should be organized by user jobs, not by transaction verticals. Mobile IA works best when primary destinations are few and task-oriented, while complex processes are handled inside guided flows rather than spread across many screens. [informationarchitectureauthority](https://informationarchitectureauthority.com/ia-for-mobile-apps.html)

### Primary navigation

- Home
- Create
- Vault
- Disputes
- Profile

### Home

Purpose:
- Start a new agreement
- Resume a draft
- Review pending signatures
- Access recently sealed agreements

### Create

Purpose:
- Launch the universal agreement builder
- Load a scenario template such as `used_vehicle_sale` or `rental_agreement`

### Vault

Purpose:
- Store drafts, sealed agreements, exports, and retention status
- Filter by type, date, and agreement status

### Disputes

Purpose:
- Start a dispute from an agreement
- Generate or resend a case pack
- Track mediator or partner status in future releases

### Profile

Purpose:
- Manage identity profile, app settings, storage plan, language, consent preferences, and help

## Domain Model

The domain model should remain small and reusable so new verticals can be introduced through template configuration instead of major data-model changes. [progress](https://www.progress.com/blogs/dynamic-forms-architecture-design)

### Core entities

| Entity | Description | Notes |
|---|---|---|
| User | A registered app account tied to phone number and profile | Phone number must be OTP-verified before the user can complete consent actions |
| Agreement | The parent transaction object | Contains type, status, draft/sealed state, timestamps |
| Party | A participant in the agreement | Stores role, name, phone, Ghana Card evidence, and verification references |
| Subject | The item, property, service, or obligation under agreement | Shape varies by scenario template |
| Term | A structured contractual term | Price, rent, deposit, date, duration, obligations |
| EvidenceItem | Photo, audio, ID scan, receipt, video, OCR extract | Includes metadata and integrity hash |
| ConsentRecord | A proof of acknowledgment or signature action | Includes actor, time, device, method, OTP verification result, and signature phrase event |
| VaultRecord | The retained package for a sealed agreement | Includes version info, PDF export references, retention state, and expiry dates |
| DisputeCase | A dispute opened from a sealed agreement | Can be created even when amendment is impossible because one party is unavailable |
| AuditEvent | Append-only event log entry | Critical for integrity and traceability |

## System Architecture

The recommended architecture is a template-driven mobile client backed by a workflow service, evidence storage layer, and document/export service. Dynamic forms are a natural fit because the same rendering engine can serve multiple transaction types while the server-delivered schema controls field visibility, required inputs, and step logic. [json-schema](https://json-schema.org/understanding-json-schema/reference/conditionals)

### Client layer

Recommended stack:
- Android-first mobile app, ideally Flutter or React Native for cross-platform flexibility
- Offline local store for draft state, queued uploads, and cached schema definitions
- Reusable component library for input, capture, review, and consent

Responsibilities:
- Render steps from schema
- Collect inputs
- Manage local draft state
- Capture photos/audio/IDs
- Queue sync operations
- Show review and consent flows

### API layer

Recommended services:
- Authentication service
- Agreement service
- Schema/template service
- Evidence service
- Consent service
- Vault/export service
- Dispute service

Responsibilities:
- Deliver scenario templates and app-config metadata
- Validate drafts and sealing rules
- Store append-only audit events
- Produce exportable agreement summaries and evidence packs

### Storage layer

Recommended storage split:
- Relational database for agreements, parties, terms, statuses, audit events
- Object storage for media files and exports
- Integrity store for hashes and version references

### Security and integrity layer

- Hash each uploaded evidence artifact on ingest
- Hash each agreement snapshot at seal time
- Store append-only audit events
- Prevent destructive edits to sealed versions
- Require separate OTP verification for each party before sealing
- Require bilateral re-authentication for any reopening workflow
- Maintain access-control boundaries between involved parties

## Component Model

The frontend should be built from reusable components so that cars, rentals, and later scenarios all render from the same visual and interaction primitives. This is consistent with schema-driven architecture, where component reuse and rule-driven field rendering are more scalable than hardcoded screen variants. [npmjs](https://www.npmjs.com/package/react-jsonschema-form-conditionals)

### Navigation components

- `BottomTabBar`
- `StepProgressHeader`
- `DraftStatusBanner`
- `PrimaryActionBar`
- `BackNextFooter`

### Input components

- `TextField`
- `PhoneField`
- `CurrencyField`
- `NumberField`
- `DateField`
- `SelectField`
- `RadioGroupField`
- `CheckboxGroupField`
- `TextAreaField`

### Capture components

- `PhotoCaptureCard`
- `MultiPhotoCaptureGrid`
- `VoiceRecorderCard`
- `IDCaptureCard`
- `OCRPreviewCard`
- `LocationStampCard`
- `ReceiptUploadCard`

### Review and status components

- `AgreementSummaryCard`
- `SectionReviewBlock`
- `MissingInfoAlert`
- `EvidenceChecklist`
- `SealStatusBadge`
- `AuditTimelinePreview`

### Consent and trust components

- `ConsentCheckbox`
- `OTPConfirmSheet`
- `SignaturePhraseInput`
- `DualPartyReviewPanel`
- `ReopenRequestBanner`
- `PostSealAnnotationComposer`
- `IntegrityNoticeBanner`

### Utility components

- `PermissionExplainerSheet`
- `OfflineSyncBanner`
- `ErrorStateCard`
- `LoadingSkeleton`
- `ShareExportSheet`

## Schema Structure

A scenario template should be versioned JSON delivered from the backend. The template should define the flow, field metadata, evidence requirements, and summary generation rules, while the mobile client remains generic. JSON Schema conditionals and rule-based field visibility are appropriate patterns for this kind of product. [json-schema](https://json-schema.org/understanding-json-schema/reference/conditionals)

### Top-level schema shape

```json
{
  "scenarioId": "used_vehicle_sale",
  "version": "1.0.0",
  "title": "Used vehicle sale",
  "description": "Capture a vehicle sale agreement and evidence pack",
  "steps": [],
  "fields": {},
  "rules": [],
  "evidenceRequirements": {},
  "summaryTemplate": {},
  "sealPolicy": {},
  "reopenPolicy": {},
  "retentionPolicy": {}
}
```

### Step schema

```json
{
  "id": "terms",
  "title": "Terms and payment",
  "type": "form",
  "fields": ["price_amount", "payment_method", "deposit_required"],
  "isSkippable": false
}
```

### Field schema

```json
{
  "price_amount": {
    "type": "currency",
    "label": "Agreed price",
    "required": true,
    "dataPath": "terms.price.amount",
    "validation": {
      "min": 0
    }
  }
}
```

### Conditional rule schema

```json
{
  "if": {
    "field": "deposit_required",
    "operator": "equals",
    "value": true
  },
  "then": {
    "show": ["deposit_amount", "deposit_due_date"],
    "require": ["deposit_amount"]
  }
}
```

### Evidence requirement schema

```json
{
  "required": [
    "party_a_ghana_card",
    "party_b_ghana_card",
    "subject_primary_photo",
    "voice_summary"
  ],
  "optional": [
    "payment_receipt",
    "video_walkthrough"
  ],
  "minimumPhotoCount": 3
}
```

### Summary template schema

```json
{
  "plainLanguageSummary": "{party_a_name} agrees to transfer {subject_label} to {party_b_name} for {price_amount} on {transaction_date}.",
  "reviewSections": [
    "parties",
    "subject",
    "condition",
    "terms",
    "evidence"
  ]
}
```

### Reopen policy schema

```json
{
  "requiresBothParties": true,
  "requiresFreshOtpForBoth": true,
  "createsNewVersion": true,
  "allowUnilateralEditIfOtherPartyUnavailable": false,
  "allowPostSealAnnotation": true,
  "allowDisputeCreation": true
}
```

## Scenario Templates

The first two scenario templates should share the same skeleton but differ in subject, condition, and terms content.

### Used vehicle sale template

```json
{
  "scenarioId": "used_vehicle_sale",
  "steps": [
    "role_select",
    "parties",
    "vehicle_details",
    "vehicle_condition",
    "terms",
    "evidence",
    "review",
    "consent",
    "seal"
  ],
  "fields": {
    "vehicle_make": {"type": "select", "required": true},
    "vehicle_model": {"type": "text", "required": true},
    "vehicle_year": {"type": "number", "required": false},
    "plate_number": {"type": "text", "required": false},
    "vin": {"type": "text", "required": false},
    "mileage": {"type": "number", "required": false},
    "known_damage_notes": {"type": "textarea", "required": false}
  }
}
```

### Rental agreement template

```json
{
  "scenarioId": "rental_agreement",
  "steps": [
    "role_select",
    "parties",
    "property_details",
    "property_condition",
    "terms",
    "evidence",
    "review",
    "consent",
    "seal"
  ],
  "fields": {
    "property_type": {"type": "select", "required": true},
    "property_address": {"type": "text", "required": true},
    "unit_number": {"type": "text", "required": false},
    "move_in_date": {"type": "date", "required": true},
    "rent_amount": {"type": "currency", "required": true},
    "deposit_required": {"type": "boolean", "required": true},
    "deposit_amount": {"type": "currency", "required": false},
    "duration_months": {"type": "number", "required": false},
    "existing_damage_notes": {"type": "textarea", "required": false}
  }
}
```

## API Specification

The backend should expose simple, scenario-oriented endpoints that support drafts, sealing, evidence upload, and exports.

### Authentication

- `POST /auth/send-otp`
- `POST /auth/verify-otp`
- `GET /me`

### Templates

- `GET /templates`
- `GET /templates/{scenarioId}`
- `GET /templates/{scenarioId}/versions/{version}`

### Agreements

- `POST /agreements`
- `GET /agreements/{agreementId}`
- `PATCH /agreements/{agreementId}`
- `POST /agreements/{agreementId}/validate`
- `POST /agreements/{agreementId}/seal`
- `GET /agreements?status=draft|pending|sealed&type=...`

### Parties

- `POST /agreements/{agreementId}/parties`
- `PATCH /agreements/{agreementId}/parties/{partyId}`

### Evidence

- `POST /agreements/{agreementId}/evidence/upload-url`
- `POST /agreements/{agreementId}/evidence`
- `GET /agreements/{agreementId}/evidence`
- `DELETE /agreements/{agreementId}/evidence/{evidenceId}` for drafts only

### Consent

- `POST /agreements/{agreementId}/consent/request-otp`
- `POST /agreements/{agreementId}/consent/confirm`
- `GET /agreements/{agreementId}/consent`

### Reopening and annotation

- `POST /agreements/{agreementId}/reopen-request`
- `POST /agreements/{agreementId}/reopen-consent/request-otp`
- `POST /agreements/{agreementId}/reopen-consent/confirm`
- `POST /agreements/{agreementId}/annotations`

### Vault and exports

- `GET /vault`
- `GET /vault/{agreementId}`
- `POST /vault/{agreementId}/export`
- `GET /vault/{agreementId}/audit-log`

### Disputes

- `POST /agreements/{agreementId}/disputes`
- `GET /disputes/{disputeId}`
- `POST /disputes/{disputeId}/case-pack`

## Example Agreement Object

```json
{
  "agreementId": "agr_01HXYZ...",
  "scenarioId": "used_vehicle_sale",
  "status": "sealed",
  "initiatorUserId": "usr_123",
  "createdAt": "2026-04-15T12:00:00Z",
  "sealedAt": "2026-04-15T12:08:12Z",
  "parties": [
    {
      "partyId": "pty_1",
      "role": "seller",
      "fullName": "Kofi Mensah",
      "phoneNumber": "+233...",
      "idDocuments": ["evd_ghana_card_1"],
      "phoneVerifiedAt": "2026-04-15T12:04:00Z"
    },
    {
      "partyId": "pty_2",
      "role": "buyer",
      "fullName": "Ama Owusu",
      "phoneNumber": "+233...",
      "idDocuments": ["evd_ghana_card_2"],
      "phoneVerifiedAt": "2026-04-15T12:05:00Z"
    }
  ],
  "subject": {
    "type": "vehicle",
    "label": "Toyota Corolla 2010",
    "attributes": {
      "make": "Toyota",
      "model": "Corolla",
      "year": 2010,
      "plateNumber": "GR-0000-20",
      "mileage": 120400
    }
  },
  "terms": {
    "price": {
      "amount": 55000,
      "currency": "GHS"
    },
    "paymentMethod": "cash",
    "handoverDate": "2026-04-16"
  },
  "evidenceIds": ["evd_1", "evd_2", "evd_3"],
  "consentRecords": ["cns_1", "cns_2"],
  "vaultRecordId": "vlt_1"
}
```

## State Model

The agreement lifecycle should be explicit and event-driven.

### Draft states

- `draft`
- `awaiting_other_party`
- `ready_for_review`
- `ready_to_seal`

### Finalized states

- `sealed`
- `reopen_requested`
- `reopened_mutual`
- `superseded`
- `annotated_post_seal`
- `archived`
- `expired`

### Dispute states

- `dispute_open`
- `case_pack_generated`
- `referred_to_partner`
- `closed`

### Allowed transitions

| From | To | Trigger |
|---|---|---|
| draft | awaiting_other_party | Second party invited or pending input |
| draft | ready_for_review | Required fields complete |
| ready_for_review | ready_to_seal | Review accepted |
| ready_to_seal | sealed | Party A OTP and Party B OTP both complete, plus signature confirmation |
| sealed | reopen_requested | One party requests mutual amendment |
| reopen_requested | reopened_mutual | Both parties re-authenticate with fresh OTP and reopening consent |
| reopened_mutual | sealed | New amended version is sealed |
| sealed | annotated_post_seal | One party adds post-seal note without changing sealed content |
| sealed | dispute_open | User raises an issue |
| sealed | archived | User archive action or retention transition |
| archived | expired | Retention window ends without extension |

## Screen-by-Screen Unified Flow

The app should use one wizard-style creation flow for both cars and rentals. Multi-step form patterns improve usability for complex mobile tasks by chunking work into short steps and supporting review before submission. [eleken](https://www.eleken.co/blog-posts/wizard-ui-pattern-explained)

### 1. Home

Primary actions:
- Create agreement
- Resume draft
- View pending signature

### 2. Choose scenario

Options:
- Used vehicle sale
- Rental agreement
- Service agreement
- Other simple agreement

Action:
- Load the latest active template for the selected scenario

### 3. Choose role

Options:
- Seller / landlord
- Buyer / tenant
- Recorder / witness

### 4. Add parties

Collect:
- Name
- Phone
- ID type
- ID image
- Optional selfie match in future version

### 5. Describe subject

Conditional branch:
- Vehicle fields if `scenarioId = used_vehicle_sale`
- Property fields if `scenarioId = rental_agreement`

### 6. Capture condition

Conditional branch:
- Vehicle photo set and damage notes
- Property photo set, room fixtures, and existing issues

### 7. Add terms

Shared structure:
- Price or rent
- Payment method
- Deposit toggle
- Start/handover date
- Special terms

### 8. Add evidence

Collect:
- Voice summary
- Additional photos
- Receipt or payment proof
- Optional witness details

### 9. Review summary

Show generated sections:
- Parties
- Subject
- Condition
- Terms
- Evidence completeness

### 10. Consent

Shared steps:
- Review statement
- Confirm checkbox
- Party A separate OTP
- Party B separate OTP
- Signature phrase

### 11. Seal success

Actions:
- View in vault
- Export/share as PDF
- Start another agreement

## Functional Requirements

### FR-1 Template loading
The app shall fetch active scenario templates from the backend and cache them locally for offline use.

### FR-2 Dynamic step rendering
The app shall render creation flows from the template's step and field definitions rather than hardcoded per-scenario screens. [progress](https://www.progress.com/blogs/dynamic-forms-architecture-design)

### FR-3 Conditional visibility
The app shall show or hide fields and steps based on rule evaluation from the active template. [json-schema](https://json-schema.org/understanding-json-schema/reference/conditionals)

### FR-4 Draft persistence
The app shall preserve incomplete agreements locally and sync them when connectivity is restored.

### FR-5 Evidence capture
The app shall support photo, audio, and ID capture from within the flow.

### FR-6 Review generation
The app shall generate a plain-language review summary before consent.

### FR-7 Dual consent
The app shall require explicit confirmation from both parties before changing agreement state to `sealed`, including a separate OTP flow for each party.

### FR-8 Identity verification minimum
The system shall require Ghana Card capture and OTP-verified phone number for each party before final consent.

### FR-9 Integrity controls
The system shall prevent direct mutation of sealed agreement content and instead create a new version or append-only event.

### FR-10 Reopening controls
The system shall require bilateral reopening with both parties re-authenticated before any sealed agreement can be amended.

### FR-11 Post-seal annotation fallback
The system shall allow post-seal annotations or dispute notes when one party is unavailable, without changing the sealed record content.

### FR-12 Vault export
The system shall generate a PDF export containing summary text, metadata, consent history, and attached evidence index.

### FR-13 Audit trail
The system shall store a timestamped audit event for every significant creation, update, consent, sealing, reopening, annotation, and dispute action.

## Non-Functional Requirements

### Performance

- Initial screen interactive within 2 seconds on standard 4G Android devices.
- Step transitions under 300ms when working from cached schema.
- Photo capture flow must tolerate upload retries and background sync.

### Reliability

- Draft data loss rate should be near zero.
- Upload retry queue should survive app restarts.

### Security

- All network traffic encrypted in transit.
- Media stored with signed URLs and access control.
- Sensitive personal data minimized and protected by role-based access.

### Accessibility and usability

- Large tap targets suitable for low-end Android devices.
- Plain-language labels.
- Multi-step flow with visible progress.
- Minimal text entry when camera or voice capture can substitute. [formsonfire](https://www.formsonfire.com/blog/mobile-form-design)

## Data and Audit Requirements

Each agreement should maintain:
- Creation timestamp
- Last update timestamp
- Seal timestamp
- Actor IDs for each event
- Device context where available
- Version hash for each sealed snapshot
- File hash for each evidence artifact
- Retention expiry date

These controls are consistent with the legal importance of reliability, origin identification, and storage integrity for electronic records in Ghana. [nita.gov](https://nita.gov.gh/wp-content/uploads/2017/12/Electronic-Transactions-Act-772.pdf)