from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_add_device_session_user_pin_otp_request"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminMfaCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code_hash", models.CharField(max_length=256)),
                ("sent_to_email", models.EmailField(max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("attempt_count", models.IntegerField(default=0)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="admin_mfa_codes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "admin_mfa_codes",
            },
        ),
        migrations.AddIndex(
            model_name="adminmfacode",
            index=models.Index(fields=["user", "created_at"], name="admin_mfa__user_id_b605a4_idx"),
        ),
        migrations.AddIndex(
            model_name="adminmfacode",
            index=models.Index(fields=["expires_at"], name="admin_mfa__expires_3c3b82_idx"),
        ),
    ]
