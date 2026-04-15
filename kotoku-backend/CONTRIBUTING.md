# Contributing to Kotoku Backend

This repository follows a modular-monolith Django structure. The goal is to keep the codebase easy to navigate, safe to change, and consistent across contributors.

## Core principles

- Keep domain logic inside domain apps under `apps/`.
- Keep `config/` limited to project wiring.
- Keep `common/` small and genuinely shared.
- Keep third-party integrations in `infrastructure/`.
- Prefer explicit modules over generic `utils.py` files.

## Project structure

Use these ownership rules when adding code:

- `config/`
  Project settings, root URLs, ASGI/WSGI entrypoints, Celery bootstrap.
- `apps/`
  Domain-owned models, serializers, views, services, selectors, tasks, tests.
- `common/`
  Shared exceptions, permissions, pagination, validators, response helpers, types.
- `infrastructure/`
  Adapters for storage, SMS, OCR, transcription, PDF, observability, and similar integrations.
- `tests/`
  Cross-app integration and end-to-end coverage.

## Rules for app code

Each domain app should generally follow this pattern:

```text
app_name/
├── api/
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── models.py
├── services.py
├── selectors.py
├── admin.py
├── apps.py
├── tests/
└── tasks.py  # only if the app owns async work
```

Follow these rules consistently:

- `models.py`
  Persistence shape only.
- `serializers.py`
  Input validation and API serialization.
- `views.py`
  Thin orchestration only.
- `services.py`
  Business rules and write operations.
- `selectors.py`
  Read/query logic.
- `tasks.py`
  Background jobs owned by the app.

## Required architecture rules

### 1. Keep views thin

Views should:

- receive the request
- validate input with serializers
- call a service or selector
- return a response

Views should not contain domain policy, workflow rules, or query-heavy logic.

### 2. Keep writes in services

Any code that changes system state belongs in `services.py` or a small service object.

Examples:

- create draft agreement
- attach party identity
- request OTP consent
- seal or reopen an agreement
- add post-seal annotations

### 3. Keep reads in selectors

Complex filtering, joins, prefetching, and read optimization belong in `selectors.py`, not in views.

### 4. Task ownership follows domain ownership

If a background job belongs to a domain, keep it in that domain app.

Examples:

- evidence processing -> `apps/evidence/tasks.py`
- vault export generation -> `apps/vault/tasks.py`
- notifications dispatch -> `apps/notifications/tasks.py`

### 5. Use one Celery app only

The project has one Celery bootstrap in [config/celery.py](/Users/asamoahoscary/Kotoku/kotoku-backend/config/celery.py). Do not add per-app Celery apps.

### 6. Audit important write paths

Important state changes must emit append-only audit events through [apps/audit/services.py](/Users/asamoahoscary/Kotoku/kotoku-backend/apps/audit/services.py).

Typical examples:

- agreement lifecycle changes
- OTP events
- evidence attachment
- vault export completion
- reopen flows
- dispute actions

## How to add a new feature

When building a new domain feature:

1. Add or update models in the owning app.
2. Put write workflows in `services.py`.
3. Put read/query workflows in `selectors.py`.
4. Expose transport logic through `api/serializers.py`, `api/views.py`, and `api/urls.py`.
5. Add app-local tests in `apps/<app>/tests/`.
6. Add integration coverage in `tests/integration/` if the workflow crosses boundaries.
7. Emit audit events for important writes.
8. Add or update docs in `docs/` when the API, workflow, or domain behavior changes.

## Shared code rules

Only place code in `common/` if it is stable, reusable, and truly shared by multiple apps.

Good fits:

- response helpers
- pagination
- generic validators
- shared exceptions
- common permission primitives

Bad fits:

- domain-specific business rules
- one-off helper functions
- app-specific policies

## Integration code rules

Put external service code in `infrastructure/`, not directly in views or services.

Examples:

- S3 clients
- SMS gateways
- OCR or transcription clients
- PDF rendering wrappers
- observability helpers

Domain services may call infrastructure adapters, but infrastructure code should not own domain policy.

## Testing expectations

Prefer this order of coverage:

- unit tests for services
- unit tests for selectors
- integration tests for important workflows
- end-to-end tests only for highest-value flows

At minimum, changes should include tests when they alter:

- domain write rules
- query behavior
- API contracts
- async workflows
- audit behavior

## Django admin guidance

Register important models in Django admin early for operational visibility.

For audit-sensitive models:

- prefer read-only fields where appropriate
- avoid admin actions that bypass service-layer rules

## Migrations guidance

- Keep migrations with the app that owns the models.
- Avoid circular dependencies between apps where possible.
- Do not mix unrelated schema changes into one migration without a good reason.

## Local development workflow

Use the documented commands:

- `make bootstrap`
- `make dev`
- `make migrate`
- `make test`
- `make lint`
- `make worker`
- `make beat`

Python 3.12+ is required.

## Documentation expectations

Update documentation when behavior changes:

- `docs/api/` for API contract changes
- `docs/architecture/` for request flow or system boundary changes
- `docs/product/` for policy or compliance-driven decisions

## Pull request checklist

Before opening a PR, verify:

- the code lives in the correct app and module
- views remain thin
- writes are in services
- reads are in selectors
- async jobs stay in the owning app
- important writes emit audit events
- tests cover the change
- docs are updated when needed
- `make lint` passes
- `make test` passes
