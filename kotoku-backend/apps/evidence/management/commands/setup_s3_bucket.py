"""Management command: configure S3 bucket CORS for browser evidence uploads.

Run this once after provisioning the production bucket, or whenever
the list of allowed web origins changes:

    python manage.py setup_s3_bucket

The command is idempotent — it overwrites the existing CORS policy.

Allowed origins are resolved from the S3_CORS_ALLOWED_ORIGINS env var
(comma-separated). If unset, it falls back to CORS_ALLOWED_ORIGINS from
Django settings, which covers the production web domain.
"""
import logging
import os

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger("kotoku")


class Command(BaseCommand):
    help = "Configure CORS and bucket policy on the S3 evidence bucket."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the CORS config that would be applied without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Resolve allowed origins: dedicated env var → Django CORS setting.
        raw_origins = os.getenv("S3_CORS_ALLOWED_ORIGINS", "")
        if raw_origins.strip():
            allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        else:
            allowed_origins = list(getattr(settings, "CORS_ALLOWED_ORIGINS", []))

        if not allowed_origins:
            self.stderr.write(
                self.style.ERROR(
                    "No allowed origins configured. Set S3_CORS_ALLOWED_ORIGINS or "
                    "CORS_ALLOWED_ORIGINS before running this command."
                )
            )
            return

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        endpoint_url = getattr(settings, "AWS_ENDPOINT_URL_S3", None) or None

        cors_config = {
            "CORSRules": [
                {
                    "AllowedOrigins": allowed_origins,
                    # PUT for direct upload; GET/HEAD for presigned view URLs;
                    # OPTIONS for CORS preflight.
                    "AllowedMethods": ["PUT", "GET", "HEAD", "OPTIONS"],
                    # Content-Type is the only header included in the presigned
                    # PUT signature since x-amz-meta-sha256 was removed.
                    "AllowedHeaders": ["Content-Type", "Authorization"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }

        self.stdout.write(f"Bucket:          {bucket}")
        self.stdout.write(f"Endpoint:        {endpoint_url or '(AWS default)'}")
        self.stdout.write(f"Allowed origins: {allowed_origins}")

        if dry_run:
            import json
            self.stdout.write(
                self.style.WARNING("Dry run — CORS config that would be applied:")
            )
            self.stdout.write(json.dumps(cors_config, indent=2))
            return

        client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME.strip(),
            config=BotoConfig(signature_version="s3v4"),
        )

        try:
            client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_config)
            self.stdout.write(
                self.style.SUCCESS(f"CORS policy applied to bucket '{bucket}'.")
            )
        except (BotoCoreError, ClientError) as exc:
            self.stderr.write(
                self.style.ERROR(f"Failed to apply CORS policy: {exc}")
            )
            raise SystemExit(1) from exc
