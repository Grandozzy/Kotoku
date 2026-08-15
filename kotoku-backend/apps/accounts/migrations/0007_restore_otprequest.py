from django.db import migrations


def _restore_otprequest_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    if "otp_requests" in existing_tables:
        return

    OTPRequest = apps.get_model("accounts", "OTPRequest")
    schema_editor.create_model(OTPRequest)


def _drop_otprequest_if_present(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    if "otp_requests" not in existing_tables:
        return

    OTPRequest = apps.get_model("accounts", "OTPRequest")
    schema_editor.delete_model(OTPRequest)


class Migration(migrations.Migration):
    """
    Migration 0006_delete_otprequest ran in production and dropped otp_requests.
    The Arkesel-only path was subsequently reversed; local OTPRequest management
    was restored in models.py and services.py but no migration re-created the table.
    This migration recreates otp_requests so production matches the current model.
    """

    dependencies = [
        (
            "accounts",
            "0005_rename_admin_mfa__user_id_b605a4_idx_admin_mfa_c_user_id_d503df_idx_and_more",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    _restore_otprequest_if_missing,
                    _drop_otprequest_if_present,
                ),
            ],
            state_operations=[],
        ),
    ]
