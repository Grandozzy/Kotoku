import secrets

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .models import Account, AdminMfaCode, User
from .tasks import send_admin_mfa_email


class AdminEmailEnrollmentForm(forms.Form):
    email = forms.EmailField(label="Admin email")


class AdminMfaCodeForm(forms.Form):
    code = forms.CharField(
        label="Authentication code",
        min_length=6,
        max_length=6,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "placeholder": "6-digit code",
            }
        ),
    )


def install_admin_mfa(site: admin.AdminSite) -> None:
    if getattr(site, "_kotoku_admin_mfa_installed", False):
        return

    original_get_urls = site.get_urls

    def _client_ip(request: HttpRequest) -> str:
        return (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR", "unknown"))

    def _consume_rate_limit(key: str, *, limit: int, ttl_seconds: int) -> bool:
        count = cache.get(key, 0)
        if count >= limit:
            return False
        if count == 0:
            cache.set(key, 1, ttl_seconds)
            return True
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, count + 1, ttl_seconds)
        return True

    def _get_redirect_target(request: HttpRequest) -> str:
        candidate = (
            request.POST.get(REDIRECT_FIELD_NAME)
            or request.GET.get(REDIRECT_FIELD_NAME)
            or reverse("admin:index")
        )
        if url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return candidate
        return reverse("admin:index")

    def _pending_user(request: HttpRequest) -> User | None:
        user_id = request.session.get("admin_preauth_user_id")
        if not user_id:
            return None
        return User.objects.filter(pk=user_id, is_active=True, is_staff=True).first()

    def _clear_pending_session(request: HttpRequest) -> None:
        for key in ("admin_preauth_user_id", "admin_preauth_backend", "admin_post_login_redirect"):
            request.session.pop(key, None)

    def _get_admin_email(user: User) -> str:
        account = getattr(user, "account", None)
        if not account:
            return ""
        return (account.email or "").strip().lower()

    def _issue_code(user: User, email: str) -> None:
        AdminMfaCode.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        raw_code = f"{secrets.randbelow(1000000):06d}"
        ttl = getattr(settings, "ADMIN_MFA_CODE_TTL_SECONDS", 600)
        AdminMfaCode.objects.create(
            user=user,
            code_hash=make_password(raw_code),
            sent_to_email=email,
            expires_at=timezone.now() + timezone.timedelta(seconds=ttl),
        )
        send_admin_mfa_email.delay(to=email, code=raw_code, ttl_seconds=ttl)

    def login_view(request: HttpRequest, extra_context=None) -> HttpResponse:
        if request.method == "GET" and site.has_permission(request):
            return redirect("admin:index")

        if request.method == "POST":
            ip_key = f"admin-login:{_client_ip(request)}"
            if not _consume_rate_limit(
                ip_key,
                limit=getattr(settings, "ADMIN_LOGIN_MAX_ATTEMPTS", 10),
                ttl_seconds=getattr(settings, "ADMIN_LOGIN_WINDOW_SECONDS", 900),
            ):
                messages.error(request, "Too many admin login attempts. Try again later.")
                form = AuthenticationForm(request=request)
            else:
                form = AuthenticationForm(request=request, data=request.POST)
        else:
            form = AuthenticationForm(request=request)

        if request.method == "POST" and form.is_valid():
            user = form.get_user()
            if not user.is_staff:
                form.add_error(None, "This account does not have admin access.")
            else:
                request.session["admin_preauth_user_id"] = str(user.pk)
                request.session["admin_preauth_backend"] = getattr(user, "backend", "")
                request.session["admin_post_login_redirect"] = _get_redirect_target(request)
                email = _get_admin_email(user)
                if email:
                    try:
                        _issue_code(user, email)
                    except Exception:
                        form.add_error(None, "Unable to send the admin authentication code.")
                    else:
                        return redirect("admin:verify-code")
                else:
                    return redirect("admin:enroll-email")

        context = {
            **site.each_context(request),
            "title": "Log in",
            "subtitle": "Admin access requires your password and a one-time email code.",
            "app_path": request.get_full_path(),
            "username": request.user.get_username() if request.user.is_authenticated else "",
            "form": form,
            REDIRECT_FIELD_NAME: _get_redirect_target(request),
        }
        if extra_context:
            context.update(extra_context)
        return render(request, "admin/login.html", context)

    def enroll_email_view(request: HttpRequest) -> HttpResponse:
        user = _pending_user(request)
        if not user:
            return redirect("admin:login")

        form = AdminEmailEnrollmentForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            existing = Account.objects.exclude(user=user).filter(email=email).exists()
            if existing:
                form.add_error("email", "That email address is already in use.")
            else:
                account, _ = Account.objects.get_or_create(
                    user=user,
                    defaults={"email": email, "phone": user.phone},
                )
                account.email = email
                if not account.phone:
                    account.phone = user.phone
                account.save(update_fields=["email", "phone", "updated_at"])
                try:
                    _issue_code(user, email)
                except Exception:
                    form.add_error(None, "Unable to send the admin authentication code.")
                else:
                    return redirect("admin:verify-code")

        context = {
            **site.each_context(request),
            "title": "Set admin email",
            "subtitle": "This email is used only for admin sign-in codes.",
            "form": form,
        }
        return render(request, "admin/enroll_email.html", context)

    def resend_code_view(request: HttpRequest) -> HttpResponse:
        user = _pending_user(request)
        if not user:
            return redirect("admin:login")

        email = _get_admin_email(user)
        if not email:
            return redirect("admin:enroll-email")

        ip_key = f"admin-mfa-resend:{_client_ip(request)}"
        if not _consume_rate_limit(
            ip_key,
            limit=getattr(settings, "ADMIN_MFA_RESEND_LIMIT", 3),
            ttl_seconds=getattr(settings, "ADMIN_MFA_WINDOW_SECONDS", 900),
        ):
            messages.error(request, "Too many resend attempts. Try again later.")
            return redirect("admin:verify-code")

        try:
            _issue_code(user, email)
        except Exception:
            messages.error(request, "Unable to resend the authentication code.")
        else:
            messages.success(request, f"A new code has been sent to {email}.")

        return redirect("admin:verify-code")

    def verify_code_view(request: HttpRequest) -> HttpResponse:
        user = _pending_user(request)
        if not user:
            return redirect("admin:login")

        email = _get_admin_email(user)
        if not email:
            return redirect("admin:enroll-email")

        form = AdminMfaCodeForm(request.POST or None)
        if request.method == "POST":
            ip_key = f"admin-mfa-ip:{_client_ip(request)}"
            user_key = f"admin-mfa-user:{user.pk}"
            allowed = all(
                (
                    _consume_rate_limit(
                        ip_key,
                        limit=getattr(settings, "ADMIN_MFA_MAX_ATTEMPTS_PER_IP", 10),
                        ttl_seconds=getattr(settings, "ADMIN_MFA_WINDOW_SECONDS", 900),
                    ),
                    _consume_rate_limit(
                        user_key,
                        limit=getattr(settings, "ADMIN_MFA_MAX_ATTEMPTS_PER_USER", 5),
                        ttl_seconds=getattr(settings, "ADMIN_MFA_WINDOW_SECONDS", 900),
                    ),
                )
            )
            if not allowed:
                form.add_error(None, "Too many authentication code attempts. Try again later.")
            elif form.is_valid():
                record = (
                    AdminMfaCode.objects
                    .filter(user=user, used_at__isnull=True)
                    .order_by("-created_at")
                    .first()
                )
                code = form.cleaned_data["code"]
                if not record or record.is_expired or not check_password(code, record.code_hash):
                    if record:
                        record.attempt_count += 1
                        record.save(update_fields=["attempt_count"])
                    form.add_error("code", "Invalid or expired code.")
                else:
                    record.used_at = timezone.now()
                    record.save(update_fields=["used_at"])
                    backend = request.session.get("admin_preauth_backend")
                    if not backend:
                        form.add_error(None, "Admin login session expired. Please try again.")
                    else:
                        auth_login(request, user, backend=backend)
                        request.session.set_expiry(
                            getattr(settings, "ADMIN_SESSION_TIMEOUT_SECONDS", 3600)
                        )
                        target = request.session.get(
                            "admin_post_login_redirect",
                            reverse("admin:index"),
                        )
                        _clear_pending_session(request)
                        return redirect(target)

        context = {
            **site.each_context(request),
            "title": "Enter authentication code",
            "subtitle": f"A sign-in code was sent to {email}.",
            "form": form,
            "email": email,
        }
        return render(request, "admin/verify_code.html", context)

    def get_urls(self: admin.AdminSite):
        urls = original_get_urls()
        custom_urls = [
            path("enroll-email/", never_cache(csrf_protect(enroll_email_view)), name="enroll-email"),
            path("verify/", never_cache(csrf_protect(verify_code_view)), name="verify-code"),
            path("resend-code/", never_cache(csrf_protect(resend_code_view)), name="resend-code"),
        ]
        return custom_urls + urls

    site.login = never_cache(csrf_protect(login_view))
    site.get_urls = get_urls.__get__(site, admin.AdminSite)
    site._kotoku_admin_mfa_installed = True
