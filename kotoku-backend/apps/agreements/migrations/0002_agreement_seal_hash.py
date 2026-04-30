from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agreements', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='agreement',
            name='seal_hash',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
