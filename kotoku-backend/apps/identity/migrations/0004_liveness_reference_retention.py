from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0003_partyidentityverification_liveness")]

    operations = [
        migrations.AddField(
            model_name="partyidentityverification",
            name="liveness_reference_delete_after",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
