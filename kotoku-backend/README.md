# Kotoku Backend

Backend scaffold for Kotoku built around Django, Django REST Framework, and Celery.

The repository follows a modular-monolith layout:
- `config/` holds project wiring only.
- `apps/` holds domain-owned models, APIs, services, selectors, and tasks.
- `common/` holds genuinely shared primitives.
- `infrastructure/` holds third-party adapters.
- `tests/` holds cross-app integration and end-to-end coverage.

Contribution rules and architectural patterns are documented in [CONTRIBUTING.md](/Users/asamoahoscary/Kotoku/kotoku-backend/CONTRIBUTING.md).

## Quick start

1. Use Python 3.12 or newer.
2. Copy `.env.example` to `.env`.
3. Run `make bootstrap`.
4. Start local dependencies with `docker compose up db redis -d`.
5. Run `make migrate`.
6. Run `make dev`.

## Running locally

- API: `make dev`
- Celery worker: `make worker`
- Celery beat: `make beat`
- Tests: `make test`
- Lint: `make lint`

## Docker development

Use the full local stack when you want the API, PostgreSQL, Redis, worker, and beat together:

```bash
docker compose up --build
```

## Architecture notes

- Views should stay thin: validate input, call a service, return a response.
- Writes belong in `services.py`.
- Reads belong in `selectors.py`.
- Async jobs live in the owning app's `tasks.py`.
- Important state changes should emit append-only audit events through `apps.audit.services`.

## Layout

- `apps/`: domain-driven Django apps.
- `config/`: settings, URLs, ASGI, WSGI, Celery bootstrap.
- `common/`: shared backend primitives.
- `infrastructure/`: adapters for storage, OCR, SMS, PDF, and observability.
- `tests/`: shared factories and cross-app tests.
