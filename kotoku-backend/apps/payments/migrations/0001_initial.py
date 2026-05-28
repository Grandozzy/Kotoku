import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_account_plan"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=100)),
                ("payload", models.JSONField()),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed", models.BooleanField(db_index=True, default=False)),
                ("error", models.TextField(blank=True)),
            ],
            options={
                "db_table": "payment_events",
                "indexes": [
                    models.Index(fields=["received_at"], name="payment_eve_receive_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "account",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to="accounts.account",
                    ),
                ),
                ("paystack_sub_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("paystack_customer_code", models.CharField(blank=True, max_length=100)),
                ("paystack_email", models.EmailField()),
                ("paystack_plan_code", models.CharField(blank=True, max_length=100)),
                ("plan_id", models.CharField(max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("active", "Active"),
                            ("paused", "Paused"),
                            ("cancelled", "Cancelled"),
                            ("past_due", "Past due"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("current_period_start", models.DateField(blank=True, null=True)),
                ("current_period_end", models.DateField(blank=True, null=True)),
                ("cancel_at_period_end", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "payment_subscriptions",
                "indexes": [
                    models.Index(fields=["status", "current_period_end"], name="payment_sub_status_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invoices",
                        to="accounts.account",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invoices",
                        to="payments.subscription",
                    ),
                ),
                ("paystack_ref", models.CharField(max_length=255, unique=True)),
                ("amount_kobo", models.IntegerField()),
                ("currency", models.CharField(default="GHS", max_length=10)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "payment_invoices",
                "indexes": [
                    models.Index(fields=["account", "status"], name="payment_inv_account_idx"),
                    models.Index(fields=["created_at"], name="payment_inv_created_idx"),
                ],
            },
        ),
    ]
