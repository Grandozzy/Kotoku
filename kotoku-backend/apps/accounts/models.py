import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from common.phone_numbers import normalize_phone_to_e164


def _default_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:16]}"


def _default_otp_id() -> str:
    return f"otp_{uuid.uuid4().hex[:16]}"


class UserManager(BaseUserManager):
    def create_user(self, phone: str, password: str | None = None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        phone = normalize_phone_to_e164(phone)
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if not password:
            raise ValueError("Superuser must have a password.")
        return self.create_user(phone, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:
        return self.phone


class Account(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="account",
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    plan = models.CharField(max_length=32, default="personal_basic", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.email


# ── Device sessions ───────────────────────────────────────────────────────────

class DeviceSession(models.Model):
    CLIENT_MOBILE = "mobile"
    CLIENT_WEB = "web"
    CLIENT_CHOICES = [(CLIENT_MOBILE, "Mobile"), (CLIENT_WEB, "Web")]

    REVOKE_LOGOUT = "logout"
    REVOKE_NEW_DEVICE = "new_device"
    REVOKE_ADMIN = "admin"
    REVOKE_SIM_SWAP = "sim_swap_suspect"
    REVOKE_SIGNOUT_ALL = "signout_all"

    id = models.CharField(
        primary_key=True,
        max_length=50,
        default=_default_session_id,
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="device_sessions",
    )
    refresh_token_hash = models.CharField(max_length=256)
    client_type = models.CharField(max_length=10, choices=CLIENT_CHOICES, default=CLIENT_MOBILE)
    device_name = models.CharField(max_length=200, blank=True)
    device_fingerprint = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "device_sessions"
        indexes = [
            models.Index(fields=["user", "is_revoked"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.id} ({self.user.phone})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


# ── User PIN ──────────────────────────────────────────────────────────────────

class UserPin(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="pin",
    )
    pin_hash = models.CharField(max_length=256)   # Argon2 hash via argon2-cffi
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_pins"

    def __str__(self) -> str:
        return f"PIN({self.user.phone})"

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and timezone.now() < self.locked_until)


# ── OTP requests ──────────────────────────────────────────────────────────────

class OTPRequest(models.Model):
    PURPOSE_LOGIN = "login"
    PURPOSE_SEAL = "seal"
    PURPOSE_REOPEN = "reopen"
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_SEAL, "Seal agreement"),
        (PURPOSE_REOPEN, "Reopen agreement"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=50,
        default=_default_otp_id,
    )
    phone = models.CharField(max_length=20)
    otp_hash = models.CharField(max_length=256)   # hashed, never plain
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_LOGIN)
    agreement_id = models.CharField(max_length=50, blank=True)  # only for seal/reopen
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.IntegerField(default=0)

    class Meta:
        db_table = "otp_requests"
        indexes = [
            models.Index(fields=["phone", "purpose", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"OTP({self.phone} / {self.purpose})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class AdminMfaCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_mfa_codes",
    )
    code_hash = models.CharField(max_length=256)
    sent_to_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.IntegerField(default=0)

    class Meta:
        db_table = "admin_mfa_codes"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"AdminMfaCode({self.user_id})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
