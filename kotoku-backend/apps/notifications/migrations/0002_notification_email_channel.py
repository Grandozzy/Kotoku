from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="subject",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="notification",
            name="channel",
            field=models.CharField(
                choices=[
                    ("sms", "SMS"),
                    ("email", "Email"),
                    ("whatsapp", "WhatsApp"),
                    ("in_app", "In-App"),
                ],
                max_length=10,
            ),
        ),
    ]
