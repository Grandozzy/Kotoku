import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evidence", "0002_initial"),
        ("parties", "0002_party_add_contact_fields"),
    ]

    operations = [
        # Make uploaded_by nullable — not known at presigned-URL generation time.
        migrations.AlterField(
            model_name="evidenceitem",
            name="uploaded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="uploaded_evidence",
                to="parties.party",
            ),
        ),
        # Allow file_hash to be blank (presigned uploads never stream bytes through Django).
        migrations.AlterField(
            model_name="evidenceitem",
            name="file_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        # New fields for the presigned upload flow.
        migrations.AddField(
            model_name="evidenceitem",
            name="evidence_type",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="evidenceitem",
            name="mime_type",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="evidenceitem",
            name="size_bytes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evidenceitem",
            name="file_key",
            field=models.CharField(blank=True, db_index=True, max_length=512),
        ),
        # Default CONFIRMED so existing rows and the legacy upload_evidence()
        # path continue to pass can_seal checks without any data backfill.
        migrations.AddField(
            model_name="evidenceitem",
            name="upload_status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("confirmed", "Confirmed")],
                db_index=True,
                default="confirmed",
                max_length=20,
            ),
        ),
    ]
