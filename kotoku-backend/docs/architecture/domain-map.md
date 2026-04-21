# Domain Map

## Entity relationships

```
User (auth)
 └── Account (profile: phone, full_name)
      └── IdentityRecord (ghana_card, passport, etc.)
           └── Party (role in an Agreement: buyer, seller, witness)
                └── Agreement
                     ├── Party (1..n)
                     ├── EvidenceItem (photos, voice notes, signatures, docs)
                     ├── ConsentRecord (one per Party, OTP-verified)
                     ├── VaultEntry (created on seal)
                     └── Dispute (raised post-seal)

Notification (owned by notifications app, triggered by services)
AuditLog (append-only, written by AuditService on every state change)
```

## Entity descriptions

### Account / User
`User` is the Django auth model. It uses `phone` as the username field and stores no password — authentication is phone + OTP only. `Account` holds the user-facing profile (full name, email). The one-to-one link is `Account.user`.

### IdentityRecord
A verified identity document linked to an `Account`. Stores the verification type (`ghana_card`, `passport`, `voter_id`, `phone`) and a reference string. An account may hold multiple identity records.

### Agreement
The central entity. Progresses through a strict state machine:

```
DRAFT ──request_consent──▶ PENDING_CONSENT ──all_consented──▶ ACTIVE
                                                                  │
                                                               seal│
                                                                  ▼
                                                              SEALED ──close──▶ CLOSED
                                                                │
                                                           reopen (within 24h)
                                                                │
                                                              ACTIVE
```

Transitions are enforced by `apps.agreements.domain.state_machine`. Policies in `apps.agreements.domain.policies` guard the preconditions for each transition (e.g. `can_seal` requires at least one `EvidenceItem`).

### Party
A named participant in an `Agreement`. Each Party links an `IdentityRecord` to an `Agreement` and carries a `role` (buyer, seller, witness, guarantor). The combination of `(agreement, identity, role)` is unique.

### EvidenceItem
A file uploaded by a `Party` to an `Agreement` while it is in ACTIVE status. Supported types: `photo`, `voice_note`, `signature`, `document`. The file is uploaded to S3/MinIO; the stored SHA-256 hash guarantees integrity. Magic-bytes validation is performed before upload.

### ConsentRecord
One record per `Party`, created when consent is requested. Contains a hashed OTP sent via SMS. When all parties verify their OTP, the agreement transitions from PENDING_CONSENT to ACTIVE. Verification is rate-limited (3 attempts, 15-minute lockout).

### VaultEntry
An immutable artifact created when an agreement is sealed. Represents the frozen state of the agreement at the point of sealing. Intended for long-term archival and legal reference.

### Dispute
A formal dispute raised against a sealed agreement. Tracks status and is linked to the agreement and the disputing party.

### Notification
A channel-agnostic outbound message (SMS, WhatsApp, email). Created by services; dispatched asynchronously by `NotificationService` → `SmsGateway` (Africa's Talking). Each notification tracks send status.

### AuditLog
An append-only log of all significant domain events (`agreement.created`, `consent.granted`, `evidence.uploaded`, etc.). Written by `AuditService.record_event()`. Never mutated after creation.

## Ownership rules

- Services in one app may **read** models from another app via selectors.
- Services in one app must **not write** to models owned by another app — go through that app's service instead.
- `AuditService` is the only cross-cutting write concern and may be called by any service.
