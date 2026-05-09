# Sprint 2 — Identity & Agreement Draft API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the 7 REST endpoints from the Sprint 2 spec so users can authenticate via phone OTP and create/manage agreement drafts.

**Architecture:** Phone-based auth using the existing `User`/`Account` models. OTP codes are cached in Redis with rate limiting. Agreement drafts use the existing `AgreementService`/`AgreementSelector` layer. Templates are a new lightweight model seeded with two scenarios. All API endpoints follow the existing pattern: `APIView` → `Serializer` → `Service`/`Selector` → `ok()` response.

**Tech Stack:** Django 5.1, DRF 3.15, PostgreSQL, Redis (cache), pytest, ruff

---

## Context for the Implementer

### What already exists on `origin/main`

| Layer | What's done |
|---|---|
| **Models** | `User` (phone-based, `AbstractBaseUser`), `Account`, `Agreement` (full lifecycle), `Party`, `IdentityRecord`, `EvidenceItem`, `ConsentRecord`, `Notification`, `VaultEntry`, `Dispute`, `AuditLog` — all with migrations |
| **Agreement service** | `AgreementService.create_draft`, `add_party`, `request_consent`, `seal_agreement`, `close_agreement`, `reopen_agreement` — all with audit events |
| **Agreement selectors** | `AgreementSelector.list_agreements`, `get_agreement_detail`, `list_party_agreements` |
| **Consent service** | `ConsentService.request_consent`, `verify_otp` (with rate limiting, hashing) |
| **Notification service** | `NotificationService.send_notification` with SMS provider |
| **API pattern** | `common.responses.ok(payload)`, `common.exceptions.DomainError`, `common.pagination.DefaultPagination` |
| **Test pattern** | Plain pytest functions, `APIClient()`, `tests/conftest.py` has `make_account` fixture, tests use SQLite in-memory via `config/settings/test.py` |

### What does NOT exist yet (this plan builds it)

1. Phone auth OTP endpoints (`send-otp`, `verify-otp`)
2. Agreement REST API layer (serializers, views, URLs)
3. Template model + seed data + endpoints
4. DRF exception handler for `DomainError`
5. Auth permission class for authenticated endpoints

### Codebase conventions

- Services: `@staticmethod` methods, keyword-only args (`*`), write operations, emit audit events
- Selectors: `@staticmethod` methods, return QuerySets, read-only
- Views: DRF `APIView`, call selectors/services, never touch ORM directly
- Serializers: `ModelSerializer` with explicit `fields` tuple
- Responses: `ok({"results": serializer.data})` or `ok({"agreement": serializer.data})`
- URLs: mounted in `config/urls.py` as `api/<appname>/`
- Tests: plain functions, `APIClient()`, `make_account` fixture from conftest
- Branch naming: `feat/short-description`
- Commit types: `feat`, `fix`, `chore` only

---

## File Map

### New files

| File | Responsibility |
|---|---|
| `apps/auth/api/serializers.py` | Auth request/response serializers |
| `apps/auth/api/views.py` | `SendOtpView`, `VerifyOtpView` |
| `apps/auth/api/urls.py` | Auth URL routing |
| `apps/auth/services.py` | `AuthService.send_otp`, `AuthService.verify_otp` |
| `apps/auth/tests/test_auth_service.py` | Unit tests for auth service |
| `apps/auth/tests/test_auth_api.py` | API integration tests |
| `apps/agreements/api/serializers.py` | Agreement serializers |
| `apps/agreements/api/views.py` | Agreement views (create, update, fetch, list) |
| `apps/agreements/api/urls.py` | Agreement URL routing |
| `apps/agreements/tests/test_agreement_api.py` | API integration tests |
| `apps/templates/models.py` | `ScenarioTemplate` model |
| `apps/templates/admin.py` | Admin registration |
| `apps/templates/api/serializers.py` | Template serializer |
| `apps/templates/api/views.py` | `TemplateListView`, `TemplateDetailView` |
| `apps/templates/api/urls.py` | Template URL routing |
| `apps/templates/selectors.py` | `TemplateSelector` |
| `apps/templates/management/commands/seed_templates.py` | Seed command for default templates |
| `apps/templates/tests/test_template_api.py` | API tests |
| `common/exception_handler.py` | DRF exception handler mapping `DomainError` → 400 |

### Modified files

| File | Change |
|---|---|
| `config/settings/base.py` | Add `apps.auth`, `apps.templates` to `INSTALLED_APPS`, add `EXCEPTION_HANDLER` to REST_FRAMEWORK |
| `config/urls.py` | Add `api/auth/`, `api/agreements/`, `api/templates/` routes |
| `apps/agreements/services.py` | Add `update_draft` method |
| `apps/agreements/selectors.py` | Add `list_templates` method (or keep in templates app) |

---

## Task 1: DRF Exception Handler for DomainError

Currently `DomainError` is a plain Python exception — when raised from a view, DRF returns a 500. We need it mapped to a structured 400 response.

**Files:**
- Create: `common/exception_handler.py`
- Modify: `config/settings/base.py`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_exception_handler.py`:

```python
from rest_framework.test import APIClient

from common.exceptions import DomainError


def test_domain_error_returns_400() -> None:
    client = APIClient()
    try:
        raise DomainError("something broke")
    except DomainError:
        import traceback
        pass

    from common.exception_handler import kotoku_exception_handler
    from rest_framework.views import exception_handler

    response = kotoku_exception_handler(
        exc=DomainError("something broke"),
        context={},
    )
    assert response is not None
    assert response.status_code == 400
    assert response.data["status"] == "error"
    assert response.data["message"] == "something broke"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd kotoku-backend && python -m pytest tests/integration/test_exception_handler.py -v`
Expected: FAIL — `kotoku_exception_handler` not found or returns `None`

- [ ] **Step 3: Write minimal implementation**

Create `common/exception_handler.py`:

```python
from rest_framework.response import Response
from rest_framework.views import exception_handler


def kotoku_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, DomainError):
        from common.exceptions import DomainError as DE

        return Response(
            {"status": "error", "message": str(exc)},
            status=400,
        )

    return response
```

- [ ] **Step 4: Wire into REST_FRAMEWORK settings**

In `config/settings/base.py`, add to the `REST_FRAMEWORK` dict:

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.exception_handler.kotoku_exception_handler",
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd kotoku-backend && python -m pytest tests/integration/test_exception_handler.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add common/exception_handler.py config/settings/base.py tests/integration/test_exception_handler.py
git commit -m "feat: add DRF exception handler for DomainError"
```

---

## Task 2: Auth App — Service Layer

Phone-based OTP auth service. Stores OTP codes in Redis cache with expiry and rate limiting. On verify, creates/updates `User` + `Account` and returns the user.

**Files:**
- Create: `apps/auth/__init__.py`
- Create: `apps/auth/apps.py`
- Create: `apps/auth/services.py`
- Create: `apps/auth/tests/test_auth_service.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/auth/__init__.py` (empty).

Create `apps/auth/apps.py`:

```python
from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth"
    label = "auth"
    verbose_name = "Auth"
```

Create `apps/auth/tests/__init__.py` (empty).

Create `apps/auth/tests/test_auth_service.py`:

```python
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import Account, User
from apps.auth.services import AuthService
from common.exceptions import DomainError


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestAuthService(TestCase):
    def setUp(self):
        cache.clear()

    def test_send_otp_creates_cache_entry(self):
        AuthService.send_otp(phone="+233501234567")
        cached = cache.get("auth_otp:+233501234567")
        assert cached is not None
        assert len(cached) == 8

    def test_send_otp_rate_limited(self):
        AuthService.send_otp(phone="+233501234567")
        with self.assertRaises(DomainError):
            AuthService.send_otp(phone="+233501234567")

    def test_verify_otp_creates_user_and_account(self):
        AuthService.send_otp(phone="+233501234567")
        otp = cache.get("auth_otp:+233501234567")
        result = AuthService.verify_otp(phone="+233501234567", otp_code=otp)
        assert result["user"].phone == "+233501234567"
        assert Account.objects.filter(user=result["user"]).exists()

    def test_verify_otp_wrong_code_raises(self):
        AuthService.send_otp(phone="+233501234567")
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="00000000")

    def test_verify_otp_expired_raises(self):
        AuthService.send_otp(phone="+233501234567")
        cache.delete("auth_otp:+233501234567")
        with self.assertRaises(DomainError):
            AuthService.verify_otp(phone="+233501234567", otp_code="12345678")

    def test_verify_otp_returns_existing_user(self):
        user = User.objects.create_user(phone="+233501234567")
        Account.objects.create(user=user, email="+233501234567@kotoku.app", phone=user.phone)
        AuthService.send_otp(phone="+233501234567")
        otp = cache.get("auth_otp:+233501234567")
        result = AuthService.verify_otp(phone="+233501234567", otp_code=otp)
        assert result["user"].pk == user.pk
        assert Account.objects.filter(user=result["user"]).count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd kotoku-backend && python -m pytest apps/auth/tests/test_auth_service.py -v`
Expected: FAIL — `apps.auth.services` not found

- [ ] **Step 3: Write the implementation**

Create `apps/auth/services.py`:

```python
import logging
import secrets

from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import Account, User
from apps.audit.services import AuditService
from common.exceptions import DomainError

logger = logging.getLogger(__name__)

_OTP_LENGTH = 8
_OTP_TTL_SECONDS = 600  # 10 minutes
_RATE_LIMIT_TTL_SECONDS = 60  # 1 minute between sends


class AuthService:
    @staticmethod
    def send_otp(*, phone: str) -> None:
        cache_key = f"auth_otp:{phone}"
        rate_key = f"auth_otp_rate:{phone}"
        if cache.get(rate_key):
            raise DomainError("OTP already sent. Please wait before requesting another.")
        otp_code = "".join(secrets.choice("0123456789") for _ in range(_OTP_LENGTH))
        cache.set(cache_key, otp_code, timeout=_OTP_TTL_SECONDS)
        cache.set(rate_key, True, timeout=_RATE_LIMIT_TTL_SECONDS)
        logger.info("OTP sent to %s", phone)
        AuditService.record_event(
            event_type="auth.otp_sent",
            entity_type="user",
            entity_id=phone,
            metadata={"channel": "sms"},
        )

    @staticmethod
    def verify_otp(*, phone: str, otp_code: str) -> dict:
        cache_key = f"auth_otp:{phone}"
        cached_otp = cache.get(cache_key)
        if cached_otp is None:
            raise DomainError("OTP has expired or was not sent. Please request a new one.")
        if cached_otp != otp_code:
            raise DomainError("Invalid OTP code.")
        cache.delete(cache_key)
        user, created = User.objects.get_or_create(phone=phone)
        if created:
            Account.objects.create(
                user=user,
                email=f"{phone}@kotoku.app",
                phone=phone,
            )
        AuditService.record_event(
            event_type="auth.otp_verified",
            entity_type="user",
            entity_id=str(user.pk),
            metadata={"new_user": created},
        )
        return {"user": user, "is_new": created}
```

- [ ] **Step 4: Register the app**

In `config/settings/base.py`, add `"apps.auth"` to `INSTALLED_APPS` (after `apps.accounts`).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd kotoku-backend && python -m pytest apps/auth/tests/test_auth_service.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Run lint**

Run: `cd kotoku-backend && make lint`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add apps/auth/ config/settings/base.py
git commit -m "feat: add phone OTP auth service with rate limiting"
```

---

## Task 3: Auth App — API Endpoints

Expose `send_otp` and `verify_otp` as REST endpoints.

**Files:**
- Create: `apps/auth/api/__init__.py`
- Create: `apps/auth/api/serializers.py`
- Create: `apps/auth/api/views.py`
- Create: `apps/auth/api/urls.py`
- Create: `apps/auth/tests/test_auth_api.py`
- Modify: `config/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/auth/api/__init__.py` (empty).

Create `apps/auth/tests/test_auth_api.py`:

```python
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestSendOtpApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_send_otp_returns_200(self):
        response = self.client.post(
            "/api/auth/send-otp/",
            {"phone": "+233501234567"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_send_otp_missing_phone_returns_400(self):
        response = self.client.post("/api/auth/send-otp/", {}, format="json")
        assert response.status_code == 400

    def test_send_otp_rate_limited_returns_400(self):
        self.client.post("/api/auth/send-otp/", {"phone": "+233501234567"}, format="json")
        response = self.client.post(
            "/api/auth/send-otp/",
            {"phone": "+233501234567"},
            format="json",
        )
        assert response.status_code == 400


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestVerifyOtpApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_verify_otp_returns_200_with_token(self):
        self.client.post("/api/auth/send-otp/", {"phone": "+233501234567"}, format="json")
        from django.core.cache import cache

        otp = cache.get("auth_otp:+233501234567")
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": "+233501234567", "otp_code": otp},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data["data"]

    def test_verify_otp_wrong_code_returns_400(self):
        self.client.post("/api/auth/send-otp/", {"phone": "+233501234567"}, format="json")
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": "+233501234567", "otp_code": "00000000"},
            format="json",
        )
        assert response.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd kotoku-backend && python -m pytest apps/auth/tests/test_auth_api.py -v`
Expected: FAIL — URL not found

- [ ] **Step 3: Create serializers**

Create `apps/auth/api/serializers.py`:

```python
from rest_framework import serializers


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=8)
```

- [ ] **Step 4: Create views**

Create `apps/auth/api/views.py`:

```python
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

from apps.auth.api.serializers import SendOtpSerializer, VerifyOtpSerializer
from apps.auth.services import AuthService
from common.responses import ok


class SendOtpView(APIView):
    def post(self, request):
        serializer = SendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.send_otp(phone=serializer.validated_data["phone"])
        return ok({"message": "OTP sent"})


class VerifyOtpView(APIView):
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthService.verify_otp(
            phone=serializer.validated_data["phone"],
            otp_code=serializer.validated_data["otp_code"],
        )
        token, _ = Token.objects.get_or_create(user=result["user"])
        return ok({"token": token.key, "is_new_user": result["is_new"]})
```

- [ ] **Step 5: Create URLs**

Create `apps/auth/api/urls.py`:

```python
from django.urls import path

from .views import SendOtpView, VerifyOtpView

urlpatterns = [
    path("send-otp/", SendOtpView.as_view(), name="auth-send-otp"),
    path("verify-otp/", VerifyOtpView.as_view(), name="auth-verify-otp"),
]
```

- [ ] **Step 6: Wire into root URLs**

In `config/urls.py`, add:

```python
path("api/auth/", include("apps.auth.api.urls")),
```

- [ ] **Step 7: Add `rest_framework.authtoken` to INSTALLED_APPS**

In `config/settings/base.py`, add `"rest_framework.authtoken"` to `INSTALLED_APPS`.

- [ ] **Step 8: Generate migration for authtoken**

Run: `cd kotoku-backend && python manage.py makemigrations authtoken`

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd kotoku-backend && python -m pytest apps/auth/tests/test_auth_api.py -v`
Expected: All 5 tests PASS

- [ ] **Step 10: Run lint**

Run: `cd kotoku-backend && make lint`

- [ ] **Step 11: Commit**

```bash
git add apps/auth/api/ apps/auth/tests/test_auth_api.py config/urls.py config/settings/base.py
git commit -m "feat: add auth API endpoints for OTP send and verify"
```

---

## Task 4: Agreement API — Serializers

DRF serializers for the agreement domain. These translate between JSON and the existing `AgreementService`/`AgreementSelector`.

**Files:**
- Create: `apps/agreements/api/serializers.py`

- [ ] **Step 1: Write the serializers**

Create `apps/agreements/api/serializers.py`:

```python
from rest_framework import serializers

from apps.agreements.models import Agreement


class AgreementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    scenario_template = serializers.CharField(
        max_length=128, required=False, default="", allow_blank=True
    )


class AgreementUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    scenario_template = serializers.CharField(
        max_length=128, required=False, allow_blank=True
    )


class PartySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    role = serializers.CharField()
    display_name = serializers.CharField()


class AgreementListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ("id", "title", "status", "scenario_template", "created_at", "updated_at")


class AgreementDetailSerializer(serializers.ModelSerializer):
    parties = PartySerializer(many=True, read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "title",
            "description",
            "status",
            "scenario_template",
            "sealed_at",
            "closed_at",
            "created_at",
            "updated_at",
            "parties",
        )
```

- [ ] **Step 2: Run lint**

Run: `cd kotoku-backend && make lint`

- [ ] **Step 3: Commit**

```bash
git add apps/agreements/api/serializers.py
git commit -m "feat: add agreement API serializers"
```

---

## Task 5: Agreement API — Add `update_draft` to AgreementService

The Sprint 2 spec requires `PATCH /agreements/{id}`. The existing `AgreementService` has `create_draft` but no update method.

**Files:**
- Modify: `apps/agreements/services.py`
- Modify: `apps/agreements/tests/test_services.py`

- [ ] **Step 1: Write the failing test**

Add to `apps/agreements/tests/test_services.py`:

```python
def test_update_draft_updates_fields(account):
    agreement = AgreementService.create_draft(
        title="Original", created_by=account, description="old desc"
    )
    updated = AgreementService.update_draft(
        agreement_id=agreement.pk,
        title="Updated",
        description="new desc",
    )
    assert updated.title == "Updated"
    assert updated.description == "new desc"


def test_update_draft_raises_if_not_draft(account):
    agreement = AgreementService.create_draft(title="Test", created_by=account)
    identity = _identity(account)
    party_a = Party.objects.create(
        agreement=agreement, identity=identity, role="buyer", display_name="A"
    )
    party_b_identity = _identity(_account(email="b@test.com"), ref="ref-b")
    Party.objects.create(
        agreement=agreement, identity=party_b_identity, role="seller", display_name="B"
    )
    AgreementService.request_consent(agreement_id=agreement.pk)
    with pytest.raises(DomainError):
        AgreementService.update_draft(agreement_id=agreement.pk, title="Nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_services.py::test_update_draft_updates_fields -v`
Expected: FAIL — `AgreementService.update_draft` not found

- [ ] **Step 3: Write the implementation**

Add to `AgreementService` in `apps/agreements/services.py`:

```python
@staticmethod
def update_draft(
    *,
    agreement_id: int,
    title: str | None = None,
    description: str | None = None,
    scenario_template: str | None = None,
) -> Agreement:
    agreement = Agreement.objects.get(pk=agreement_id)
    if agreement.status != AgreementStatus.DRAFT:
        raise DomainError("Can only update a draft agreement")
    update_fields = ["updated_at"]
    if title is not None:
        agreement.title = title
        update_fields.append("title")
    if description is not None:
        agreement.description = description
        update_fields.append("description")
    if scenario_template is not None:
        agreement.scenario_template = scenario_template
        update_fields.append("scenario_template")
    agreement.save(update_fields=update_fields)
    AuditService.record_event(
        event_type="agreement.updated",
        entity_type="agreement",
        entity_id=str(agreement.pk),
        actor=str(agreement.created_by_id),
        metadata={"updated_fields": update_fields},
    )
    return agreement
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_services.py -v`
Expected: All tests PASS (including existing ones)

- [ ] **Step 5: Run lint**

Run: `cd kotoku-backend && make lint`

- [ ] **Step 6: Commit**

```bash
git add apps/agreements/services.py apps/agreements/tests/test_services.py
git commit -m "feat: add update_draft method to AgreementService"
```

---

## Task 6: Agreement API — Views and URLs

Wire up the agreement REST endpoints.

**Files:**
- Create: `apps/agreements/api/views.py`
- Create: `apps/agreements/api/urls.py`
- Modify: `config/urls.py`

- [ ] **Step 1: Create views**

Create `apps/agreements/api/views.py`:

```python
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.api.serializers import (
    AgreementCreateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
    AgreementUpdateSerializer,
)
from apps.agreements.selectors import AgreementSelector
from apps.agreements.services import AgreementService
from common.responses import ok


class AgreementCreateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AgreementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = request.user.account
        agreement = AgreementService.create_draft(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            scenario_template=serializer.validated_data.get("scenario_template", ""),
            created_by=account,
        )
        return ok(
            {"agreement": AgreementDetailSerializer(agreement).data},
            status_code=201,
        )


class AgreementListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AgreementSelector.list_agreements(
            account_id=request.user.account.pk,
            status=request.query_params.get("status"),
        )
        from common.pagination import DefaultPagination

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AgreementListSerializer(page, many=True)
        return ok({"results": serializer.data})


class AgreementDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        agreement = AgreementSelector.get_agreement_detail(agreement_id)
        return ok({"agreement": AgreementDetailSerializer(agreement).data})


class AgreementUpdateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, agreement_id: int):
        serializer = AgreementUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        agreement = AgreementService.update_draft(
            agreement_id=agreement_id,
            **serializer.validated_data,
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})
```

- [ ] **Step 2: Update `ok()` to support custom status codes**

Modify `common/responses.py`:

```python
from rest_framework.response import Response


def ok(payload: dict, status_code: int = 200) -> Response:
    return Response({"status": "ok", "data": payload}, status=status_code)
```

- [ ] **Step 3: Create URLs**

Create `apps/agreements/api/urls.py`:

```python
from django.urls import path

from .views import (
    AgreementCreateView,
    AgreementDetailView,
    AgreementListView,
    AgreementUpdateView,
)

urlpatterns = [
    path("", AgreementCreateView.as_view(), name="agreement-create"),
    path("", AgreementListView.as_view(), name="agreement-list"),
    path("<int:agreement_id>/", AgreementDetailView.as_view(), name="agreement-detail"),
    path("<int:agreement_id>/", AgreementUpdateView.as_view(), name="agreement-update"),
]
```

**Note:** The above won't work because Django can't distinguish two views on the same path by method alone when they're separate classes. Fix by using a combined view or separate paths. Correct approach — use a single view for the collection that handles GET and POST:

Revised `apps/agreements/api/urls.py`:

```python
from django.urls import path

from .views import (
    AgreementCollectionView,
    AgreementDetailView,
)

urlpatterns = [
    path("", AgreementCollectionView.as_view(), name="agreement-collection"),
    path("<int:agreement_id>/", AgreementDetailView.as_view(), name="agreement-detail"),
]
```

Revised `apps/agreements/api/views.py`:

```python
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.api.serializers import (
    AgreementCreateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
    AgreementUpdateSerializer,
)
from apps.agreements.selectors import AgreementSelector
from apps.agreements.services import AgreementService
from common.pagination import DefaultPagination
from common.responses import ok


class AgreementCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AgreementSelector.list_agreements(
            account_id=request.user.account.pk,
            status=request.query_params.get("status"),
        )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AgreementListSerializer(page, many=True)
        return ok({"results": serializer.data})

    def post(self, request):
        serializer = AgreementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = request.user.account
        agreement = AgreementService.create_draft(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            scenario_template=serializer.validated_data.get("scenario_template", ""),
            created_by=account,
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data}, status_code=201)


class AgreementDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int):
        agreement = AgreementSelector.get_agreement_detail(agreement_id)
        return ok({"agreement": AgreementDetailSerializer(agreement).data})

    def patch(self, request, agreement_id: int):
        serializer = AgreementUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        agreement = AgreementService.update_draft(
            agreement_id=agreement_id,
            **serializer.validated_data,
        )
        return ok({"agreement": AgreementDetailSerializer(agreement).data})
```

- [ ] **Step 4: Wire into root URLs**

In `config/urls.py`, add:

```python
path("api/agreements/", include("apps.agreements.api.urls")),
```

- [ ] **Step 5: Commit**

```bash
git add apps/agreements/api/views.py apps/agreements/api/urls.py config/urls.py common/responses.py
git commit -m "feat: add agreement API views and URL routing"
```

---

## Task 7: Agreement API — Integration Tests

Test all agreement endpoints end-to-end.

**Files:**
- Create: `apps/agreements/tests/test_agreement_api.py`

- [ ] **Step 1: Write the tests**

Create `apps/agreements/tests/test_agreement_api.py`:

```python
import pytest
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Account, User


@pytest.fixture()
def authenticated_client():
    user = User.objects.create_user(phone="+233500000001")
    account = Account.objects.create(
        user=user, email="test@kotoku.app", phone=user.phone
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, account


@pytest.mark.django_db
class TestAgreementCreateApi:
    def test_create_agreement_returns_201(self, authenticated_client):
        client, _ = authenticated_client
        response = client.post(
            "/api/agreements/",
            {"title": "Car Sale", "scenario_template": "used_vehicle_sale"},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]["agreement"]
        assert data["title"] == "Car Sale"
        assert data["status"] == "draft"
        assert data["scenario_template"] == "used_vehicle_sale"

    def test_create_agreement_missing_title_returns_400(self, authenticated_client):
        client, _ = authenticated_client
        response = client.post("/api/agreements/", {}, format="json")
        assert response.status_code == 400

    def test_create_agreement_unauthenticated_returns_401(self):
        response = APIClient().post(
            "/api/agreements/", {"title": "Test"}, format="json"
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestAgreementListApi:
    def test_list_agreements_returns_200(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        AgreementService.create_draft(title="A1", created_by=account)
        AgreementService.create_draft(title="A2", created_by=account)
        response = client.get("/api/agreements/", format="json")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 2


@pytest.mark.django_db
class TestAgreementDetailApi:
    def test_get_agreement_returns_200(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(title="Detail Test", created_by=account)
        response = client.get(f"/api/agreements/{agreement.pk}/", format="json")
        assert response.status_code == 200
        data = response.json()["data"]["agreement"]
        assert data["title"] == "Detail Test"

    def test_get_nonexistent_agreement_returns_404(self, authenticated_client):
        client, _ = authenticated_client
        response = client.get("/api/agreements/99999/", format="json")
        assert response.status_code == 404


@pytest.mark.django_db
class TestAgreementUpdateApi:
    def test_update_draft_returns_200(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(title="Original", created_by=account)
        response = client.patch(
            f"/api/agreements/{agreement.pk}/",
            {"title": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]["agreement"]
        assert data["title"] == "Updated"

    def test_update_non_draft_returns_400(self, authenticated_client):
        client, account = authenticated_client
        from apps.agreements.services import AgreementService

        agreement = AgreementService.create_draft(title="Test", created_by=account)
        from apps.agreements.domain.enums import AgreementStatus

        agreement.status = AgreementStatus.SEALED
        agreement.save()
        response = client.patch(
            f"/api/agreements/{agreement.pk}/",
            {"title": "Nope"},
            format="json",
        )
        assert response.status_code == 400
```

- [ ] **Step 2: Run tests**

Run: `cd kotoku-backend && python -m pytest apps/agreements/tests/test_agreement_api.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add apps/agreements/tests/test_agreement_api.py
git commit -m "feat: add agreement API integration tests"
```

---

## Task 8: Templates App — Model and Seed Data

Lightweight `ScenarioTemplate` model that stores scenario definitions for `used_vehicle_sale` and `rental_agreement`.

**Files:**
- Create: `apps/templates/__init__.py`
- Create: `apps/templates/apps.py`
- Create: `apps/templates/models.py`
- Create: `apps/templates/admin.py`
- Create: `apps/templates/selectors.py`
- Create: `apps/templates/management/__init__.py`
- Create: `apps/templates/management/commands/__init__.py`
- Create: `apps/templates/management/commands/seed_templates.py`
- Create: `apps/templates/tests/__init__.py`
- Create: `apps/templates/tests/test_template_selector.py`

- [ ] **Step 1: Write the failing test**

Create `apps/templates/__init__.py` (empty).

Create `apps/templates/apps.py`:

```python
from django.apps import AppConfig


class TemplatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.templates"
    verbose_name = "Templates"
```

Create `apps/templates/tests/__init__.py` (empty).

Create `apps/templates/tests/test_template_selector.py`:

```python
import pytest

from apps.templates.models import ScenarioTemplate
from apps.templates.selectors import TemplateSelector


@pytest.mark.django_db
class TestTemplateSelector:
    def test_list_templates_returns_all(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale",
            name="Used Vehicle Sale",
            description="Agreement for buying/selling a used vehicle",
            field_definitions={"vehicle_make": {"type": "string", "required": True}},
        )
        ScenarioTemplate.objects.create(
            slug="rental_agreement",
            name="Rental Agreement",
            description="Agreement for renting a property or vehicle",
            field_definitions={"rental_period": {"type": "string", "required": True}},
        )
        result = TemplateSelector.list_templates()
        assert result.count() == 2

    def test_get_by_slug_returns_template(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale",
            name="Used Vehicle Sale",
            description="desc",
            field_definitions={},
        )
        template = TemplateSelector.get_by_slug("used_vehicle_sale")
        assert template.slug == "used_vehicle_sale"

    def test_get_by_slug_not_found_raises(self):
        from common.exceptions import DomainError

        with pytest.raises(DomainError):
            TemplateSelector.get_by_slug("nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd kotoku-backend && python -m pytest apps/templates/tests/test_template_selector.py -v`
Expected: FAIL

- [ ] **Step 3: Create the model**

Create `apps/templates/models.py`:

```python
from django.db import models


class ScenarioTemplate(models.Model):
    slug = models.SlugField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    field_definitions = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"
```

- [ ] **Step 4: Create admin**

Create `apps/templates/admin.py`:

```python
from django.contrib import admin

from apps.templates.models import ScenarioTemplate


@admin.register(ScenarioTemplate)
class ScenarioTemplateAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "version", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("slug", "name")
    readonly_fields = ("created_at", "updated_at")
```

- [ ] **Step 5: Create selectors**

Create `apps/templates/selectors.py`:

```python
from apps.templates.models import ScenarioTemplate
from common.exceptions import DomainError


class TemplateSelector:
    @staticmethod
    def list_templates():
        return ScenarioTemplate.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def get_by_slug(slug: str) -> ScenarioTemplate:
        try:
            return ScenarioTemplate.objects.get(slug=slug, is_active=True)
        except ScenarioTemplate.DoesNotExist:
            raise DomainError(f"Template '{slug}' not found") from None
```

- [ ] **Step 6: Register the app and generate migration**

Add `"apps.templates"` to `INSTALLED_APPS` in `config/settings/base.py`.

Run: `cd kotoku-backend && python manage.py makemigrations templates`

- [ ] **Step 7: Create seed command**

Create the `management/commands/seed_templates.py`:

```python
from django.core.management.base import BaseCommand

from apps.templates.models import ScenarioTemplate

TEMPLATES = [
    {
        "slug": "used_vehicle_sale",
        "name": "Used Vehicle Sale Agreement",
        "description": "Agreement for the sale and purchase of a used vehicle between two parties.",
        "field_definitions": {
            "vehicle_make": {"type": "string", "required": True, "label": "Vehicle Make"},
            "vehicle_model": {"type": "string", "required": True, "label": "Vehicle Model"},
            "vehicle_year": {"type": "integer", "required": True, "label": "Year of Manufacture"},
            "vin_chassis": {"type": "string", "required": True, "label": "VIN / Chassis Number"},
            "sale_price": {"type": "decimal", "required": True, "label": "Sale Price (GHS)"},
            "odometer_reading": {"type": "integer", "required": False, "label": "Odometer Reading (km)"},
            "payment_method": {
                "type": "choice",
                "required": True,
                "label": "Payment Method",
                "choices": ["cash", "bank_transfer", "mobile_money"],
            },
        },
    },
    {
        "slug": "rental_agreement",
        "name": "Rental Agreement",
        "description": "Agreement for renting a vehicle or property between two parties.",
        "field_definitions": {
            "item_description": {
                "type": "string",
                "required": True,
                "label": "Item Being Rented",
            },
            "rental_period_start": {
                "type": "date",
                "required": True,
                "label": "Rental Start Date",
            },
            "rental_period_end": {
                "type": "date",
                "required": True,
                "label": "Rental End Date",
            },
            "rental_amount": {
                "type": "decimal",
                "required": True,
                "label": "Rental Amount (GHS)",
            },
            "payment_schedule": {
                "type": "choice",
                "required": True,
                "label": "Payment Schedule",
                "choices": ["daily", "weekly", "monthly"],
            },
            "deposit_amount": {
                "type": "decimal",
                "required": False,
                "label": "Security Deposit (GHS)",
            },
        },
    },
]


class Command(BaseCommand):
    help = "Seed scenario templates for MVP"

    def handle(self, *args, **options):
        for template_data in TEMPLATES:
            obj, created = ScenarioTemplate.objects.update_or_create(
                slug=template_data["slug"],
                defaults={
                    "name": template_data["name"],
                    "description": template_data["description"],
                    "field_definitions": template_data["field_definitions"],
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} template: {obj.slug}")
        self.stdout.write(self.style.SUCCESS("Templates seeded successfully"))
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd kotoku-backend && python -m pytest apps/templates/tests/test_template_selector.py -v`
Expected: All 3 tests PASS

- [ ] **Step 9: Run lint**

Run: `cd kotoku-backend && make lint`

- [ ] **Step 10: Commit**

```bash
git add apps/templates/ config/settings/base.py
git commit -m "feat: add ScenarioTemplate model, selectors, and seed command"
```

---

## Task 9: Templates App — API Endpoints

Expose templates as read-only endpoints.

**Files:**
- Create: `apps/templates/api/__init__.py`
- Create: `apps/templates/api/serializers.py`
- Create: `apps/templates/api/views.py`
- Create: `apps/templates/api/urls.py`
- Create: `apps/templates/tests/test_template_api.py`
- Modify: `config/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/templates/api/__init__.py` (empty).

Create `apps/templates/tests/test_template_api.py`:

```python
import pytest
from rest_framework.test import APIClient

from apps.templates.models import ScenarioTemplate


@pytest.mark.django_db
class TestTemplateListApi:
    def test_list_templates_returns_200(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale", name="Used Vehicle Sale", field_definitions={}
        )
        ScenarioTemplate.objects.create(
            slug="rental_agreement", name="Rental Agreement", field_definitions={}
        )
        response = APIClient().get("/api/templates/", format="json")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 2

    def test_list_templates_empty(self):
        response = APIClient().get("/api/templates/", format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestTemplateDetailApi:
    def test_get_template_by_slug_returns_200(self):
        ScenarioTemplate.objects.create(
            slug="used_vehicle_sale",
            name="Used Vehicle Sale",
            field_definitions={"vehicle_make": {"type": "string"}},
        )
        response = APIClient().get("/api/templates/used_vehicle_sale/", format="json")
        assert response.status_code == 200
        data = response.json()["data"]["template"]
        assert data["slug"] == "used_vehicle_sale"
        assert "vehicle_make" in data["field_definitions"]

    def test_get_template_not_found_returns_404(self):
        response = APIClient().get("/api/templates/nonexistent/", format="json")
        assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd kotoku-backend && python -m pytest apps/templates/tests/test_template_api.py -v`
Expected: FAIL — URL not found

- [ ] **Step 3: Create serializers**

Create `apps/templates/api/serializers.py`:

```python
from rest_framework import serializers

from apps.templates.models import ScenarioTemplate


class ScenarioTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioTemplate
        fields = ("slug", "name", "description", "field_definitions", "version", "updated_at")
```

- [ ] **Step 4: Create views**

Create `apps/templates/api/views.py`:

```python
from rest_framework.views import APIView

from apps.templates.api.serializers import ScenarioTemplateSerializer
from apps.templates.selectors import TemplateSelector
from common.responses import ok


class TemplateListView(APIView):
    def get(self, request):
        qs = TemplateSelector.list_templates()
        from common.pagination import DefaultPagination

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ScenarioTemplateSerializer(page, many=True)
        return ok({"results": serializer.data})


class TemplateDetailView(APIView):
    def get(self, request, slug: str):
        template = TemplateSelector.get_by_slug(slug)
        return ok({"template": ScenarioTemplateSerializer(template).data})
```

- [ ] **Step 5: Create URLs**

Create `apps/templates/api/urls.py`:

```python
from django.urls import path

from .views import TemplateDetailView, TemplateListView

urlpatterns = [
    path("", TemplateListView.as_view(), name="template-list"),
    path("<str:slug>/", TemplateDetailView.as_view(), name="template-detail"),
]
```

- [ ] **Step 6: Wire into root URLs**

In `config/urls.py`, add:

```python
path("api/templates/", include("apps.templates.api.urls")),
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd kotoku-backend && python -m pytest apps/templates/tests/test_template_api.py -v`
Expected: All 4 tests PASS

- [ ] **Step 8: Run lint**

Run: `cd kotoku-backend && make lint`

- [ ] **Step 9: Commit**

```bash
git add apps/templates/api/ apps/templates/tests/test_template_api.py config/urls.py
git commit -m "feat: add template API endpoints for listing and detail"
```

---

## Task 10: Seed Templates and Verify Full Sprint 2

Seed the template data and run all tests end-to-end.

- [ ] **Step 1: Run seed command**

Run: `cd kotoku-backend && python manage.py migrate && python manage.py seed_templates`

- [ ] **Step 2: Run all tests**

Run: `cd kotoku-backend && make test`
Expected: All tests PASS

- [ ] **Step 3: Run lint**

Run: `cd kotoku-backend && make lint`
Expected: No errors

- [ ] **Step 4: Verify Sprint 2 endpoint checklist**

| Endpoint | Expected |
|---|---|
| `POST /api/auth/send-otp/` | 200 with valid phone |
| `POST /api/auth/verify-otp/` | 200 with valid OTP, returns token |
| `POST /api/agreements/` | 201, creates draft |
| `PATCH /api/agreements/{id}/` | 200, updates draft |
| `GET /api/agreements/{id}/` | 200, returns detail |
| `GET /api/templates/` | 200, lists templates |
| `GET /api/templates/{slug}/` | 200, returns template |

- [ ] **Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "chore: verify all Sprint 2 endpoints pass"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Every Sprint 2 backend work item (auth endpoints, OTP foundation, agreement models, template endpoints, draft API, audit logging) is covered by a task.
- [x] **Placeholder scan:** No TBD, TODO, or "implement later" patterns. All code is concrete.
- [x] **Type consistency:** Method signatures match between service, selector, serializer, and view layers. `ok()` updated consistently. `AgreementStatus` enum matches model choices.
- [x] **Edge cases:** Rate limiting on OTP, wrong OTP, expired OTP, non-draft update rejection, 404 for missing agreements/templates, unauthenticated access rejection.
