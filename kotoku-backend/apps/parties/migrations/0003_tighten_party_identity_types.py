from django.db import migrations, models


def migrate_other_id_type(apps, schema_editor):
    Party = apps.get_model("parties", "Party")
    Party.objects.filter(id_type="other").update(id_type="national_id")


class Migration(migrations.Migration):
    dependencies = [
        ("parties", "0002_party_add_contact_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_other_id_type, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="party",
            name="id_type",
            field=models.CharField(
                choices=[
                    ("ghana_card", "Ghana Card"),
                    ("passport", "Passport"),
                    ("national_id", "National ID Card"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="party",
            name="id_number",
            field=models.CharField(max_length=128),
        ),
    ]
