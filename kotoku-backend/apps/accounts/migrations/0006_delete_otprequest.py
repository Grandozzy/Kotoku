# Generated manually — drop OTPRequest table after Arkesel OTP migration.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_rename_admin_mfa__user_id_b605a4_idx_admin_mfa_c_user_id_d503df_idx_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="OTPRequest",
        ),
    ]
