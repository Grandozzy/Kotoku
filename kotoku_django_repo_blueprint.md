# Kotoku Django App Folder Structure and Repo Blueprint

## Overview

Kotoku should use a modular-monolith Django repository structure with domain apps grouped under a shared `apps/` directory, split settings by environment, and clear separation between business logic, query logic, infrastructure integrations, and task execution. This approach is consistent with common Django production structure guidance and modular monolith recommendations, which emphasize explicit module boundaries and keeping business logic out of views.[cite:117][cite:124][cite:126]

The repository should optimize for three realities: a mobile-first API product, background-job-heavy workflows, and a small team that needs fast onboarding and low architectural confusion. Celery integration should be organized so there is one project-level Celery app configuration while task definitions live close to the domain modules they belong to.[cite:127][cite:130]

## Repo Goals

- Keep the codebase easy for Samuel, Gap Lenz collaborators, and AI co-engineering to navigate.
- Preserve a clean path from MVP to early scale without jumping to microservices too early.[cite:117]
- Make it obvious where business rules, queries, serializers, tasks, and integrations belong.[cite:126]
- Support environment-specific settings and production deployment hygiene.[cite:128][cite:134]

## Recommended Top-Level Structure

```text
kotoku-backend/
├── manage.py
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── Makefile
├── docker-compose.yml
├── Dockerfile
├── docs/
├── scripts/
├── config/
├── apps/
├── common/
├── infrastructure/
├── tests/
└── output/  # optional local-generated artifacts, excluded in production
```

## Suggested Folder Tree

```text
kotoku-backend/
├── manage.py
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── docs/
│   ├── architecture/
│   │   ├── backend-overview.md
│   │   ├── request-flows.md
│   │   └── domain-map.md
│   ├── api/
│   │   ├── auth.md
│   │   ├── agreements.md
│   │   └── vault.md
│   └── product/
│       └── policy-decisions.md
├── scripts/
│   ├── bootstrap.sh
│   ├── run_dev.sh
│   ├── seed_demo_data.py
│   └── wait_for_db.sh
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   ├── celery.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── local.py
│       ├── test.py
│       └── production.py
├── apps/
│   ├── accounts/
│   │   ├── migrations/
│   │   ├── api/
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── permissions.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── identity/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── validators.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── agreements/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── domain/
│   │   │   ├── enums.py
│   │   │   ├── policies.py
│   │   │   └── state_machine.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── parties/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── evidence/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tasks.py
│   │   ├── storage.py
│   │   ├── hashing.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── consent/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tasks.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── vault/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tasks.py
│   │   ├── pdf.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── disputes/
│   │   ├── migrations/
│   │   ├── api/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── notifications/
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   └── sms_provider.py
│   │   ├── tasks.py
│   │   ├── tests/
│   │   └── __init__.py
│   ├── audit/
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tests/
│   │   └── __init__.py
│   └── health/
│       ├── api/
│       ├── apps.py
│       └── __init__.py
├── common/
│   ├── __init__.py
│   ├── constants.py
│   ├── exceptions.py
│   ├── pagination.py
│   ├── permissions.py
│   ├── responses.py
│   ├── validators.py
│   ├── mixins.py
│   ├── logging.py
│   └── types.py
├── infrastructure/
│   ├── __init__.py
│   ├── db/
│   ├── storage/
│   │   ├── s3.py
│   │   └── urls.py
│   ├── sms/
│   │   └── gateway.py
│   ├── ocr/
│   │   └── client.py
│   ├── transcription/
│   │   └── client.py
│   ├── pdf/
│   │   └── renderer.py
│   └── observability/
│       ├── metrics.py
│       └── tracing.py
├── tests/
│   ├── factories/
│   ├── integration/
│   ├── e2e/
│   └── conftest.py
└── requirements/  # optional if not using only pyproject.toml
```

## Why This Structure Works

A production Django project benefits from explicit environment-specific settings, app grouping by domain, and keeping business logic outside of views. Shared guidance on Django project structure consistently recommends splitting settings, grouping apps under an `apps/` namespace, and separating service logic from transport-layer code.[cite:126][cite:128][cite:132]

This layout also fits Celery integration well because the project-level Celery app can live in `config/celery.py`, while domain-specific tasks stay inside the relevant app's `tasks.py`, which keeps ownership clear and task discovery straightforward.[cite:127][cite:130]

## Folder Responsibilities

### `config/`

This should contain project wiring, not business logic.

Use it for:
- Django settings
- root URLs
- ASGI/WSGI entrypoints
- Celery app bootstrap

Do not put domain code here.

### `apps/`

This is the heart of the codebase. Each app should map to a business domain rather than a generic technical concern. Modular monolith guidance emphasizes defining boundaries around business capabilities so that logic for a domain stays together rather than being spread randomly across the project.[cite:117][cite:124]

### `common/`

Only put truly shared primitives here:
- exceptions
- generic permissions
- pagination
- response helpers
- common validators

Do not turn `common/` into a dumping ground.

### `infrastructure/`

This should contain external integration code:
- S3 storage adapter
- SMS gateway client
- OCR/transcription clients
- PDF renderer wrapper
- metrics and tracing helpers

This helps keep third-party SDK logic out of domain apps.

### `tests/`

Keep cross-app integration and end-to-end tests here, while app-specific unit tests stay inside each app. This pattern makes local module ownership clear while still supporting full-system validation.[cite:126]

## Recommended Internal Pattern per App

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
└── tasks.py  # only if the app owns async jobs
```

### Rule of thumb

- `models.py` = persistence shape
- `serializers.py` = input/output validation and API serialization
- `views.py` = thin orchestration only
- `services.py` = business rules and write operations
- `selectors.py` = query/read logic
- `tasks.py` = background jobs for that domain

Keeping views thin and centralizing business logic in service-style modules is a recurring recommendation in Django structure guidance because it improves maintainability and testing.[cite:125][cite:126]

## Repo Blueprint Rules

### Rule 1: Keep views thin

Views should receive the request, validate input through serializers, call services, and return responses. They should not contain agreement state logic, OTP policy, or retention policy.

### Rule 2: Keep writes in services

Anything that changes system state belongs in a service function or service object.

Examples:
- create draft agreement
- attach party identity
- request bilateral OTP consent
- seal agreement
- reopen agreement
- add post-seal annotation

### Rule 3: Keep reads in selectors

Selectors should hold read/query logic so performance tuning, prefetching, and filtering do not get buried in views.

### Rule 4: Task ownership follows domain ownership

If a task belongs to evidence, it lives in `apps/evidence/tasks.py`. If it belongs to vault export generation, it lives in `apps/vault/tasks.py`.

### Rule 5: Add one Celery app only

The project should have a single Celery bootstrap in `config/celery.py`, with `autodiscover_tasks()` so app-level tasks are found automatically.[cite:127][cite:130]

### Rule 6: Audit every important write path

Agreement lifecycle changes, OTP events, evidence attachment, PDF export completion, reopening, and dispute actions should all write append-only audit events.

## Settings Blueprint

Use split settings files:

- `base.py` — shared settings
- `local.py` — local dev overrides
- `test.py` — test settings
- `production.py` — secure production settings

Production guidance commonly recommends separate settings modules, environment variables for secrets, and PostgreSQL-focused production configuration such as connection reuse and strict host settings.[cite:128]

### Example environment variable groups

- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- Database: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Redis/Celery: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- Storage: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`
- SMS/OTP: `SMS_API_KEY`, `SMS_SENDER_ID`
- Observability: `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT`

## Suggested Root Files

### `README.md`
Should include:
- project purpose
- local setup
- how to run API and workers
- test commands
- architecture notes

### `Makefile`
Useful commands:
- `make dev`
- `make migrate`
- `make test`
- `make lint`
- `make worker`
- `make beat`

### `docker-compose.yml`
For local development:
- django api
- postgres
- redis
- celery worker
- celery beat

### `.env.example`
Provide safe placeholders for all required environment variables.

## Suggested Starter Conventions

### Naming

- Use plural domain app names only when it reads naturally; otherwise prefer clarity over rigid style.
- Keep serializer, service, and selector names explicit.
- Avoid generic modules like `utils.py` inside every app.

### Testing

- Unit-test services and selectors first.
- Integration-test important workflows: draft creation, evidence upload metadata, OTP confirmation, seal flow, PDF generation callback.
- End-to-end test only the highest-value paths.

### Migrations

- Keep migrations owned by the app that owns the models.
- Avoid cross-app circular model dependencies where possible.

### Admin

- Register key models in Django admin early for operational visibility.
- Add read-only fields for audit-sensitive data.

## First Repo Milestone

The first useful backend skeleton should include these apps and files wired correctly:

- `accounts`
- `identity`
- `agreements`
- `evidence`
- `consent`
- `vault`
- `audit`
- `notifications`
- `health`
- `config/celery.py`
- split settings
- Docker + local compose
- base Makefile
- root README

That is enough to give Samuel a clean backend foundation before implementing full business logic.

## Minimal First Commit Blueprint

```text
feat: initialize kotoku django backend blueprint
- add config with split settings
- add DRF and Celery wiring
- add apps namespace and core domain apps
- add common and infrastructure packages
- add Dockerfile, compose, Makefile, env example
- add baseline health endpoint and README
```

## Recommended Next Step

After this repo structure is approved, the next artifact should be either:
- Django model definitions for the first core entities, or
- API request/response payloads for auth, agreements, evidence, and consent.
