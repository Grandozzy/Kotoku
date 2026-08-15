from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0002_partyidentityverification"),
    ]

    operations = [
        migrations.AddField(
            model_name="partyidentityverification",
            name="liveness_session_id",
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name="partyidentityverification",
            name="liveness_status",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="partyidentityverification",
            name="liveness_confidence",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="partyidentityverification",
            name="liveness_reference_s3_key",
            field=models.CharField(blank=True, max_length=512),
        ),
    ]
