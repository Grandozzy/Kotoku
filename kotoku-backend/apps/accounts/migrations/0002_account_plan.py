from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="plan",
            field=models.CharField(default="personal_basic", max_length=32, db_index=True),
        ),
    ]
