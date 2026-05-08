# Kotoku

> **"Don't take their word for it. Take evidence for it."**

Kotoku is a trust and evidence platform for informal transactions. It lets two parties capture the state of a deal — photos, identity documents, agreed terms — confirm bilateral consent via SMS OTP, and seal the result into a tamper-evident, timestamped vault. Every sealed agreement is a legally recognisable evidence pack under Ghana's Electronic Transactions Act (Act 772).

---

## Why Kotoku exists

Informal agreements drive everyday economic life in Ghana — used cars change hands, rooms get rented, goods are exchanged — with nothing more than a verbal promise. When things go wrong, there is no record. Kotoku closes that gap: a five-minute capture process produces something you can actually show.

> *"Good agreements make good friends."*
> *"Record it today. Rest easy tomorrow."*
> *"The handshake, with receipts."*

---

## Products

| Product | Status | Description |
|---|---|---|
| **Kotoku Mobile** (Android / iOS) | Active development | React Native / Expo; primary capture surface |
| **Kotoku Web** | In planning | Next.js 15; dashboard, evidence upload, vault |
| **Kotoku API** | Active development | Django REST Framework backend serving both clients |

---

## Monorepo layout

```
Kotoku/
├── kotoku-backend/        Django API — agreements, vault, consent, disputes
├── Kotoku-frontend/
│   ├── kotoku-mobile/     React Native / Expo mobile app
│   └── kotoku-web/        Next.js web app (in progress)
└── docs/                  Architecture, product, and legal reference
```

---

## Quick start (backend)

```bash
cd kotoku-backend
cp .env.example .env          # fill in DB, Redis, S3, AT credentials
docker compose up -d          # postgres + redis + minio
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

See [`kotoku-backend/docs/architecture/backend-overview.md`](kotoku-backend/docs/architecture/backend-overview.md) for the full stack picture.

---

## Quick start (mobile)

```bash
cd Kotoku-frontend/kotoku-mobile
cp .env.example .env          # set EXPO_PUBLIC_API_URL
npm install
npx expo start
```

---

## Ghana digital evidence law

Kotoku's sealed record is designed to satisfy the admissibility requirements of Ghana's **Electronic Transactions Act, 2008 (Act 772)**. This section explains the legal framework and how each product decision maps to it.

### Core legislation

| Act | Relevance |
|---|---|
| Electronic Transactions Act, 2008 (Act 772) | Primary framework: admissibility, integrity, originator identification |
| Electronic Transactions Regulations, 2011 (LI 1902) | Technical requirements for electronic signatures and records |
| Evidence Act, 1975 (NRCD 323) | Foundational evidence law; business records exception |
| Data Protection Act, 2012 (Act 843) | Personal data processing; consent as lawful basis |
| Alternative Dispute Resolution Act, 2010 (Act 798) | Mediation and arbitration framework underpinning the disputes module |

### Electronic Transactions Act, 2008 — key provisions

**Section 7 — Legal recognition**
An electronic communication or electronic record shall not be denied legal effect, validity, or enforceability solely on the ground that it is in electronic form.

**Section 8 — Writing requirement**
Where any law requires information to be in writing, that requirement is satisfied by an electronic record if the information is accessible for subsequent reference.

**Section 9 — Signature requirement**
Where any law requires a signature, an electronic signature satisfies that requirement if it is reliable and appropriate in the circumstances. Kotoku's bilateral OTP — a one-time code issued to a verified phone number tied to a named party — constitutes an electronic signature for the purposes of this section.

**Section 12 — Admissibility and evidential weight**

> *"An electronic record shall not be denied admissibility in any legal proceedings on the sole ground that it is in electronic form."*

Evidential weight depends on four factors:

1. Reliability of the method used to generate or store the record.
2. Reliability of the method used to ensure integrity of the record.
3. The method used to identify the originator.
4. Any other relevant factor.

### How Kotoku satisfies each Section 12 factor

| Factor | Kotoku implementation |
|---|---|
| **Reliable generation** | Agreement state is written atomically; every field, party, and evidence item is persisted before the seal is computed |
| **Integrity** | SHA-256 hash computed over the full agreement snapshot at sealing; stored in `VaultEntry.seal_hash`; re-computable for verification |
| **Tamper-evident storage** | VaultEntry is append-only; `archived` flag and `retain_until` enforce lifecycle; no in-place edits after sealing |
| **Originator identification** | Ghana Card photo + masked ID number per party; phone verified via SMS OTP before any party can consent; `sealed_at` ISO 8601 timestamp |
| **Audit trail** | Append-only `AuditLog` records every state transition (created → draft → active → sealed → archived) with actor, timestamp, and metadata |
| **OTP as electronic signature** | One OTP per party, purpose-scoped (`consent` or `reopen_consent`), tied to verified phone number, stored in `ConsentRecord` with `confirmed_at` |

### Data Protection Act, 2012 (Act 843)

Kotoku processes personal data (phone numbers, identity photos, agreement terms) under the lawful basis of **explicit consent**. Each party provides an OTP-confirmed consent record before their data is included in a sealed agreement. Key obligations:

- Data is collected for a specific, explicit purpose (the named agreement).
- Parties can request annotations or raise disputes; the original sealed record is immutable.
- Retention periods are enforced automatically (`retain_until`); expired entries are archived by a scheduled task.

### Alternative Dispute Resolution Act, 2010 (Act 798)

Ghana's ADR framework makes mediation and arbitration a common first step before litigation. Kotoku's dispute module is designed as a **pre-mediation evidence pack**: when a dispute is raised, the sealed vault entry (PDF, seal hash, party identities, evidence photos, consent timestamps) gives a mediator or arbitrator a complete factual record to work from without either party needing to reconstruct events from memory.

### Practical standing

While Kotoku's sealed record does not replace a lawyer-drafted contract for complex commercial transactions, it provides:

- A timestamped, hashed, party-consented record that a magistrate, mediator, or arbitrator can examine.
- Clear identification of who agreed, when, and to what specific terms.
- Photo evidence of the asset's condition at the time of handover.
- An audit trail showing no modifications were made after sealing.

This is materially stronger than a verbal agreement or an unsigned WhatsApp message, and it is designed to be admissible under Act 772 Section 12.

---

## Supported agreement scenarios (v1)

| Scenario | Required evidence | Required roles |
|---|---|---|
| Used vehicle sale | ≥ 3 vehicle photos + ID photo per party | buyer, seller |
| Room rental | ≥ 2 property photos + ID photo per party + condition photo if deposit set | landlord, tenant |

---

## Key API endpoints

| Resource | Endpoint |
|---|---|
| Auth (OTP) | `POST /api/auth/otp/request/`, `POST /api/auth/otp/verify/` |
| Agreements | `GET/POST /api/agreements/` |
| Parties | `POST/PATCH/GET /api/agreements/{id}/parties/` |
| Evidence | `POST /api/agreements/{id}/evidence/initiate/`, `POST /api/agreements/{id}/evidence/{eid}/confirm/` |
| Consent | `POST /api/agreements/{id}/consent/request/`, `POST /api/agreements/{id}/consent/confirm/` |
| Vault | `GET /api/vault/`, `GET /api/vault/{id}/` |
| PDF export | `POST /api/vault/{id}/export/`, `POST /api/vault/{id}/retry-export/` |
| Reopen | `POST /api/agreements/{id}/reopen/request/` |
| Disputes | `GET/POST /api/agreements/{id}/disputes/` |
| Annotations | `GET/POST /api/agreements/{id}/annotations/` |

Full API docs: [`kotoku-backend/docs/api/`](kotoku-backend/docs/api/)

---

## Contributing

This is a private monorepo. Branches follow the pattern `feat/<scope>`, `fix/<scope>`. All changes go through PR to `main`. See [`kotoku-backend/docs/architecture/`](kotoku-backend/docs/architecture/) for conventions.
