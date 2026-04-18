from django.conf import settings


def build_storage_url(path: str) -> str:
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{path.lstrip('/')}"
