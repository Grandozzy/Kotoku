from unittest.mock import patch

from django.test import override_settings

from infrastructure.storage.s3 import S3StorageClient


@override_settings(
    AWS_STORAGE_BUCKET_NAME="kotoku-evidence",
    AWS_S3_REGION_NAME="eu-west-1",
    AWS_ACCESS_KEY_ID="test-key",
    AWS_SECRET_ACCESS_KEY="test-secret",
    AWS_ENDPOINT_URL_S3="https://kotoku-evidence.s3.eu-west-1.amazonaws.com",
    AWS_S3_EXTERNAL_URL="",
)
def test_upload_ignores_bucket_hosted_aws_endpoint_for_signing():
    with patch("infrastructure.storage.s3.boto3.client") as mock_client:
        mock_client.return_value.put_object.return_value = {}

        url = S3StorageClient().upload(
            "exports/test.pdf",
            b"%PDF",
            content_type="application/pdf",
        )

    _, kwargs = mock_client.call_args
    assert kwargs["endpoint_url"] is None
    assert url == (
        "https://kotoku-evidence.s3.eu-west-1.amazonaws.com/exports/test.pdf"
    )


@override_settings(
    AWS_STORAGE_BUCKET_NAME="kotoku-evidence",
    AWS_S3_REGION_NAME="eu-west-1",
    AWS_ACCESS_KEY_ID="test-key",
    AWS_SECRET_ACCESS_KEY="test-secret",
    AWS_ENDPOINT_URL_S3="https://storage.example.com",
    AWS_S3_EXTERNAL_URL="",
)
def test_upload_keeps_custom_s3_endpoint_for_signing_and_url_building():
    with patch("infrastructure.storage.s3.boto3.client") as mock_client:
        mock_client.return_value.put_object.return_value = {}

        url = S3StorageClient().upload(
            "exports/test.pdf",
            b"%PDF",
            content_type="application/pdf",
        )

    _, kwargs = mock_client.call_args
    assert kwargs["endpoint_url"] == "https://storage.example.com"
    assert url == "https://storage.example.com/kotoku-evidence/exports/test.pdf"


@override_settings(
    AWS_STORAGE_BUCKET_NAME="kotoku-evidence",
    AWS_S3_REGION_NAME="eu-west-1",
    AWS_ACCESS_KEY_ID="test-key",
    AWS_SECRET_ACCESS_KEY="test-secret",
    AWS_ENDPOINT_URL_S3="",
    AWS_S3_EXTERNAL_URL="https://kotoku-evidence.s3.eu-west-1.amazonaws.com",
)
def test_build_object_url_does_not_duplicate_bucket_for_bucket_hosted_external_url():
    with patch("infrastructure.storage.s3.boto3.client") as mock_client:
        mock_client.return_value.put_object.return_value = {}

        url = S3StorageClient().upload(
            "exports/test.pdf",
            b"%PDF",
            content_type="application/pdf",
        )

    assert url == (
        "https://kotoku-evidence.s3.eu-west-1.amazonaws.com/exports/test.pdf"
    )


@override_settings(
    AWS_STORAGE_BUCKET_NAME="kotoku-evidence",
    AWS_S3_REGION_NAME="eu-west-1",
    AWS_ACCESS_KEY_ID="test-key",
    AWS_SECRET_ACCESS_KEY="test-secret",
    AWS_ENDPOINT_URL_S3="",
    AWS_S3_EXTERNAL_URL="",
)
def test_upload_includes_checksum_and_metadata_when_provided():
    with patch("infrastructure.storage.s3.boto3.client") as mock_client:
        mock_client.return_value.put_object.return_value = {}

        S3StorageClient().upload(
            "exports/test.pdf",
            b"%PDF",
            content_type="application/pdf",
            checksum_sha256="48c76d8e2f8d73c014f3535dd3f7f135f4a724c8f9909a7f9fbca9a3b7a9ac0e",
        )

    put_kwargs = mock_client.return_value.put_object.call_args.kwargs
    assert put_kwargs["Metadata"]["sha256"] == (
        "48c76d8e2f8d73c014f3535dd3f7f135f4a724c8f9909a7f9fbca9a3b7a9ac0e"
    )
    assert "ChecksumSHA256" in put_kwargs
