import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscriptions",
                to="accounts.account",
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="replaced_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replaces",
                to="payments.subscription",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("active", "Active"),
                    ("paused", "Paused"),
                    ("cancelled", "Cancelled"),
                    ("past_due", "Past due"),
                    ("expired", "Expired"),
                    ("replaced", "Replaced"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="subscription",
            index=models.Index(fields=["account", "status"], name="payment_sub_account_idx"),
        ),
        migrations.CreateModel(
            name="SubscriptionCheckout",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=255, unique=True)),
                ("target_plan_id", models.CharField(max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("charged", "Charged"),
                            ("provider_created", "Provider created"),
                            ("cancelled", "Cancelled"),
                            ("failed", "Failed"),
                            ("superseded", "Superseded"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("authorization_url", models.TextField(blank=True)),
                ("access_code", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription_checkouts",
                        to="accounts.account",
                    ),
                ),
                (
                    "activated_subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activation_checkouts",
                        to="payments.subscription",
                    ),
                ),
                (
                    "replaces_subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="replacement_checkouts",
                        to="payments.subscription",
                    ),
                ),
            ],
            options={
                "db_table": "payment_subscription_checkouts",
                "indexes": [
                    models.Index(fields=["account", "status"], name="payment_subc_account_idx"),
                    models.Index(fields=["created_at"], name="payment_subc_created_idx"),
                ],
            },
        ),
    ]
