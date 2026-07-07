import logging
from urllib.parse import urlparse

import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings

logger = logging.getLogger("kotoku")


def _endpoint(name: str) -> str | None:
    """Return the setting value, or None if absent/blank (boto3 rejects empty strings)."""
    val = getattr(settings, name, None)
    if isinstance(val, str):
        val = val.strip() or None
    return val


def _is_aws_s3_endpoint(url: str | None) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return host.endswith(".amazonaws.com") and (
        host.startswith("s3.") or ".s3." in host
    )


def _is_bucket_hosted_url(url: str | None) -> bool:
    if not url:
        return False
    bucket = settings.AWS_STORAGE_BUCKET_NAME.lower()
    host = urlparse(url).netloc.lower()
    return host == f"{bucket}.s3.amazonaws.com" or host.startswith(f"{bucket}.s3.")


def _client_endpoint(name: str) -> str | None:
    endpoint_url = _endpoint(name)
    if _is_aws_s3_endpoint(endpoint_url):
        return None
    return endpoint_url


def _get_client(external: bool = False):
    if external:
        endpoint_url = _client_endpoint("AWS_S3_EXTERNAL_URL") or _client_endpoint("AWS_ENDPOINT_URL_S3")
    else:
        endpoint_url = _client_endpoint("AWS_ENDPOINT_URL_S3")
    config_kwargs = {"signature_version": "s3v4"}
    path_style = bool(endpoint_url)
    if path_style:
        config_kwargs["s3"] = {"addressing_style": "path"}

    region = settings.AWS_S3_REGION_NAME.strip()
    key_id = settings.AWS_ACCESS_KEY_ID or ""
    session_token = getattr(settings, "AWS_SESSION_TOKEN", "") or ""
    logger.info(
        "[S3] _get_client external=%s endpoint_url=%r region=%r path_style=%s key_id_prefix=%r has_session_token=%s",
        external,
        endpoint_url,
        region,
        path_style,
        key_id[:8],
        bool(session_token),
    )

    client_kwargs = {
        "endpoint_url": endpoint_url,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": region,
        "config": BotoConfig(**config_kwargs),
    }
    session_token = getattr(settings, "AWS_SESSION_TOKEN", "")
    if session_token:
        client_kwargs["aws_session_token"] = session_token

    return boto3.client(
        "s3",
        **client_kwargs,
    )


def _build_url_from_base(base_url: str, key: str) -> str:
    base = base_url.rstrip("/")
    if _is_bucket_hosted_url(base):
        return f"{base}/{key}"
    return f"{base}/{settings.AWS_STORAGE_BUCKET_NAME}/{key}"


def _build_object_url(key: str) -> str:
    external_url = _endpoint("AWS_S3_EXTERNAL_URL")
    if external_url:
        return _build_url_from_base(external_url, key)
    endpoint_url = _endpoint("AWS_ENDPOINT_URL_S3")
    if endpoint_url and not _is_aws_s3_endpoint(endpoint_url):
        return _build_url_from_base(endpoint_url, key)
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME.strip()}.amazonaws.com/{key}"


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

    def generate_presigned_view_url(
        self,
        key: str,
        *,
        content_type: str = "",
        expires_in: int = 900,
    ) -> str:
        client = _get_client(external=True)
        params = {
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key,
            "ResponseContentDisposition": "inline",
        }
        if content_type:
            params["ResponseContentType"] = content_type
        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in,
        )

    def generate_presigned_upload_url(
        self, key: str, content_type: str, checksum_sha256: str, expires_in: int = 900
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
        # Only Content-Type is included in the presigned signature.
        # The checksum is verified server-side in confirm_upload via HEAD object.
        return url, {
            "Content-Type": content_type,
        }

    def head_object(self, key: str) -> dict:
        client = _get_client()
        response = client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
        )
        return {
            "content_length": response.get("ContentLength"),
            "content_type": response.get("ContentType", ""),
            "etag": str(response.get("ETag", "")).strip('"'),
            "metadata": response.get("Metadata", {}),
        }

    def build_object_url(self, key: str) -> str:
        return _build_object_url(key)
