# Backend Overview

## What it is

Kotoku backend is a **modular Django monolith** exposing a REST API over Django REST Framework. It handles the full lifecycle of informal agreements — identity verification, party consent, evidence capture, agreement sealing, and dispute resolution.

## Technology stack

| Layer | Technology |
|-------|-----------|
| API | Django 5.x + Django REST Framework |
| Database | PostgreSQL 16 (psycopg3) |
| Async workers | Celery 5.x with Redis broker |
| File storage | AWS S3 (or MinIO locally) |
| SMS | Africa's Talking API |
| Error tracking | Sentry SDK |
| Auth | Phone-based OTP (custom `AbstractBaseUser`) |

## Module structure

```
kotoku-backend/
├── apps/          # Domain-owned Django apps
├── config/        # Project wiring only (settings, urls, celery, wsgi/asgi)
├── common/        # Shared primitives (exceptions, pagination, responses)
├── infrastructure/# Third-party adapters (S3, SMS, OCR, observability)
├── tests/         # Cross-app integration and shared fixtures
└── docs/          # Architecture, API, and product documentation
```

## Domain apps

| App | Owns |
|-----|------|
| `accounts` | User authentication model (phone-based OTP), Account profile |
| `identity` | IdentityRecord — verified ID documents linked to an account |
| `agreements` | Agreement lifecycle, state machine, policies |
| `parties` | Party — a named role within an agreement, linked to an identity |
| `evidence` | EvidenceItem — files (photos, voice notes, signatures, documents) |
| `consent` | ConsentRecord — OTP-based per-party consent |
| `vault` | VaultEntry — immutable sealed agreement artifact |
| `disputes` | Dispute — raised against a sealed agreement |
| `notifications` | Notification — channel-agnostic outbound message |
| `audit` | AuditLog — append-only event stream |
| `health` | Health and readiness probes |

## Code conventions

Every domain app follows this internal layout:

- `models.py` — persistence shape only, no business logic
- `services.py` — all writes and state mutations; wrapped in `@transaction.atomic`
- `selectors.py` — all reads and queries; never writes
- `tasks.py` — Celery background jobs owned by the app
- `api/` — thin views that validate input, delegate to services/selectors, return responses
- `tests/` — unit and integration tests per app

## Deployment topology

```
                    ┌─────────────┐
            HTTP    │  Django API  │
Client ──────────▶  │  (gunicorn)  │
                    └──────┬──────┘
                           │ DB / cache
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         PostgreSQL      Redis       AWS S3
              ▲            ▲
              │            │ broker / results
              └────────────┤
                    ┌──────┴──────┐
                    │   Celery    │
                    │  worker(s)  │
                    └─────────────┘
```

Celery beat (scheduler) runs alongside the worker for periodic tasks. In local development both run as separate processes started via `make worker` and `make beat`, or together via `docker compose up`.
