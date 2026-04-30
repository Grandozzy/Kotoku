"""Restructure VaultEntry: drop evidence_item + sealed_at, add pdf_status /
retain_until / updated_at, and convert the agreement FK to a OneToOneField."""

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vault', '0001_initial'),
        ('agreements', '0002_agreement_seal_hash'),
    ]

    operations = [
        # 1. Drop the columns that no longer belong.
        migrations.RemoveField(model_name='vaultentry', name='evidence_item'),
        migrations.RemoveField(model_name='vaultentry', name='sealed_at'),

        # 2. Convert the FK to a OneToOneField (unique constraint added).
        migrations.AlterField(
            model_name='vaultentry',
            name='agreement',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='vault_entry',
                to='agreements.agreement',
            ),
        ),

        # 3. Add new fields.
        migrations.AddField(
            model_name='vaultentry',
            name='pdf_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('generating', 'Generating'),
                    ('ready', 'Ready'),
                    ('failed', 'Failed'),
                ],
                db_index=True,
                default='pending',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='vaultentry',
            name='retain_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vaultentry',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
