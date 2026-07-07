import os

# DATABASE_URL and other vars are injected by `railway run`
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.contrib.auth import get_user_model

from apps.accounts.models import Account

User = get_user_model()

phone = os.getenv("ADMIN_PHONE", "").strip()
password = os.getenv("ADMIN_PASSWORD", "")
email = os.getenv("ADMIN_EMAIL", "").strip().lower()

if not phone or not password:
    raise SystemExit("ADMIN_PHONE and ADMIN_PASSWORD are required.")

user, created = User.objects.get_or_create(phone=phone)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password(password)
user.save()

if email:
    account, _ = Account.objects.get_or_create(
        user=user,
        defaults={"email": email, "phone": user.phone},
    )
    account.email = email
    if not account.phone:
        account.phone = user.phone
    account.save(update_fields=["email", "phone", "updated_at"])

print("Superuser created." if created else "Superuser updated.")
