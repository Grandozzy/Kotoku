# Architecture Decision Log

Decisions made during the sprint baseline that future contributors should understand.

---

## ADR-001: Phone-based OTP authentication (no passwords)

**Decision:** Use phone number as the username field on a custom `AbstractBaseUser`. Users authenticate via a one-time code sent to their phone — no passwords are stored.

**Why:** Kotoku targets users in Ghana who are more likely to have reliable mobile numbers than email addresses. OTP over SMS matches the existing mental model for financial transactions in the region.

**Consequences:**
- Password reset flows do not exist; lost-phone recovery requires a separate support process (not yet implemented).
- The `User` model calls `set_unusable_password()` on creation.
- OTP codes are 8 digits, hashed with SHA-256, and rate-limited to 3 attempts per 15 minutes.

---

## ADR-002: Modular monolith over microservices

**Decision:** A single Django process with domain-separated apps (`apps/`) rather than separate services per domain.

**Why:** The team is small. The domains are not independently scalable at this stage. A monolith with clear internal boundaries is faster to build and safer to refactor. The internal structure (services, selectors, domain layer per app) makes extraction to services a viable future path.

**Consequences:**
- All apps share one PostgreSQL database. Cross-domain queries are possible but discouraged outside selectors.
- A single Celery worker handles all async work.

---

## ADR-003: Service / selector pattern (no fat models, no fat views)

**Decision:** Business logic lives in `services.py` (writes) and `selectors.py` (reads). Models hold only persistence shape. Views are thin orchestrators.

**Why:** Fat models create implicit coupling. Fat views make logic untestable. The service/selector split makes it obvious where to look for a given behaviour and keeps views interchangeable (REST today, GraphQL or CLI tomorrow).

**Consequences:**
- Services must be the only entry point for writes. Nothing writes directly to the ORM from a view or another app's service.
- All state-mutating service methods must use `@transaction.atomic` and `select_for_update()` when reading before writing.

---

## ADR-004: Agreement state machine is the source of truth for status transitions

**Decision:** All agreement status transitions go through `apps.agreements.domain.state_machine.next_state()`. No code sets `agreement.status` directly to a string value.

**Why:** Without a single transition table, it becomes easy to introduce invalid states (e.g. jumping from DRAFT to SEALED). The state machine raises `DomainError` on invalid transitions, making bugs visible immediately.

**Consequences:**
- Adding a new status or transition requires updating `_TRANSITIONS` in `state_machine.py` and adding a policy in `policies.py` if the transition has preconditions.

---

## ADR-005: Evidence files are validated by magic bytes, not file extension

**Decision:** `EvidenceService.upload_evidence()` checks the first bytes of the file against known signatures for the declared `file_type` before any upload.

**Why:** File extensions are trivially spoofed. Magic bytes provide a minimal content-type guarantee without requiring a native library like `libmagic`.

**Consequences:**
- Maximum file size is 50 MB (enforced before upload, not by S3).
- Supported types per `file_type`: photo (JPEG, PNG), voice_note (WAV, OGG, MP3), signature (PNG, JPEG), document (PDF, JPEG, PNG).

---

## ADR-006: OTP information leakage is intentionally suppressed

**Decision:** `ConsentService.verify_otp()` returns the same error message regardless of whether the record doesn't exist, is already granted, has expired, or has a wrong code.

**Why:** Different error messages allow an attacker to enumerate which consent records exist and their current state. The specific failure reason is logged server-side for debugging.

**Consequences:**
- Users cannot distinguish "wrong code" from "code expired" from the API response. The mobile client should guide users with UI-level messaging based on context (e.g. display expiry time proactively).

---

## ADR-007: S3 storage client is custom, not django-storages

**Decision:** `infrastructure/storage/s3.py` implements a thin `S3StorageClient` using boto3 directly rather than using `django-storages` file storage backend.

**Why:** Evidence files are stored with content-addressable keys (SHA-256 hash) and are never served directly via Django. The django-storages `FileField` abstraction does not fit this model well.

**Consequences:**
- `django-storages` is still installed (used by production settings for static/media files) but is not used for evidence.
- Local dev uses MinIO. The `AWS_ENDPOINT_URL_S3` setting switches the boto3 client endpoint automatically.

---

## ADR-008: Audit log is append-only

**Decision:** `AuditLog` records are created by `AuditService.record_event()` and are never updated or deleted.

**Why:** The audit log is the forensic record for agreement disputes. Mutability would undermine its value as evidence.

**Consequences:**
- No admin actions or management commands should update or delete `AuditLog` rows.
- The model has no `updated_at` field by design.
