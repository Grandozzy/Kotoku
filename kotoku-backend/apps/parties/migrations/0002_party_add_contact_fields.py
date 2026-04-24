import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parties", "0001_initial"),
        ("identity", "0001_initial"),
    ]

    operations = [
        # Drop the old (agreement, identity, role) constraint.
        migrations.RemoveConstraint(
            model_name="party",
            name="unique_party_per_agreement_role",
        ),
        # Make identity nullable — counterparty is linked after they authenticate.
        migrations.AlterField(
            model_name="party",
            name="identity",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="parties",
                to="identity.identityrecord",
            ),
        ),
        # New contact fields captured at party-creation time.
        migrations.AddField(
            model_name="party",
            name="phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="party",
            name="id_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ghana_card", "Ghana Card"),
                    ("passport", "Passport"),
                    ("other", "Other"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="party",
            name="id_number",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="party",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        # Add LANDLORD / TENANT to role choices (data-only; Django choices are not
        # enforced at the DB level, so no column-type change is needed).
        migrations.AlterField(
            model_name="party",
            name="role",
            field=models.CharField(
                choices=[
                    ("buyer", "Buyer"),
                    ("seller", "Seller"),
                    ("landlord", "Landlord"),
                    ("tenant", "Tenant"),
                    ("witness", "Witness"),
                ],
                max_length=20,
            ),
        ),
        # Replace with tighter (agreement, role) uniqueness.
        migrations.AddConstraint(
            model_name="party",
            constraint=models.UniqueConstraint(
                fields=["agreement", "role"],
                name="unique_role_per_agreement",
            ),
        ),
    ]
