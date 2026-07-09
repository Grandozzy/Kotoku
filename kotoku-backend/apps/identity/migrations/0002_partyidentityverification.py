from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parties", "0003_tighten_party_identity_types"),
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartyIdentityVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("verified", "Verified"), ("failed", "Failed"), ("manual_review_required", "Manual review required")], db_index=True, default="pending", max_length=32)),
                ("entered_pin", models.CharField(blank=True, max_length=128)),
                ("entered_full_name", models.CharField(blank=True, max_length=255)),
                ("ocr_pin", models.CharField(blank=True, max_length=128)),
                ("ocr_full_name", models.CharField(blank=True, max_length=255)),
                ("front_evidence_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("back_evidence_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("selfie_evidence_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("front_text", models.TextField(blank=True)),
                ("back_text", models.TextField(blank=True)),
                ("face_match_score", models.FloatField(blank=True, null=True)),
                ("failure_codes", models.JSONField(blank=True, default=list)),
                ("detail", models.TextField(blank=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("party", models.OneToOneField(on_delete=models.CASCADE, related_name="identity_verification", to="parties.party")),
            ],
        ),
    ]
