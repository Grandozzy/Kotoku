import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings


def _get_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=BotoConfig(signature_version="s3v4"),
    )


class S3StorageClient:
    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        client = _get_client()
        client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        client = _get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )
