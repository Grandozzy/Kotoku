from django.db import migrations, models

import apps.accounts.models


class Migration(migrations.Migration):
    """
    Migration 0006_delete_otprequest ran in production and dropped otp_requests.
    The Arkesel-only path was subsequently reversed; local OTPRequest management
    was restored in models.py and services.py but no migration re-created the table.
    This migration recreates otp_requests so production matches the current model.
    """

    dependencies = [
        (
            "accounts",
            "0005_rename_admin_mfa__user_id_b605a4_idx_admin_mfa_c_user_id_d503df_idx_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="OTPRequest",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=apps.accounts.models._default_otp_id,
                        max_length=50,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("phone", models.CharField(max_length=20)),
                ("otp_hash", models.CharField(max_length=256)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("login", "Login"),
                            ("seal", "Seal agreement"),
                            ("reopen", "Reopen agreement"),
                        ],
                        default="login",
                        max_length=20,
                    ),
                ),
                ("agreement_id", models.CharField(blank=True, max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("is_used", models.BooleanField(default=False)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("attempt_count", models.IntegerField(default=0)),
            ],
            options={
                "db_table": "otp_requests",
                "indexes": [
                    models.Index(
                        fields=["phone", "purpose", "is_used"],
                        name="otp_request_phone_19a050_idx",
                    ),
                    models.Index(
                        fields=["expires_at"],
                        name="otp_request_expires_21a7df_idx",
                    ),
                ],
            },
        ),
    ]
