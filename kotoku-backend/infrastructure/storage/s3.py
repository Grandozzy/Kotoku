import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings


def _get_client(external: bool = False):
    if external:
        endpoint_url = getattr(settings, "AWS_S3_EXTERNAL_URL", None) or getattr(settings, "AWS_ENDPOINT_URL_S3", None)
    else:
        endpoint_url = getattr(settings, "AWS_ENDPOINT_URL_S3", None)
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=BotoConfig(signature_version="s3v4"),
    )


def _build_object_url(key: str) -> str:
    external_url = getattr(settings, "AWS_S3_EXTERNAL_URL", "")
    if external_url:
        return f"{external_url.rstrip('/')}/{settings.AWS_STORAGE_BUCKET_NAME}/{key}"
    endpoint_url = getattr(settings, "AWS_ENDPOINT_URL_S3", None)
    if endpoint_url:
        return f"{endpoint_url.rstrip('/')}/{settings.AWS_STORAGE_BUCKET_NAME}/{key}"
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"


class S3StorageClient:
    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        client = _get_client()
        client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return _build_object_url(key)

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        client = _get_client(external=True)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )

    def generate_presigned_upload_url(
        self, key: str, content_type: str, expires_in: int = 900
    ) -> tuple[str, dict]:
        client = _get_client(external=True)
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return url, {"Content-Type": content_type}

    def build_object_url(self, key: str) -> str:
        return _build_object_url(key)
