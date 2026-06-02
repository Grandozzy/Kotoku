#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL_S3:-${AWS_S3_ENDPOINT_URL:-http://minio:9000}}"
BUCKET="${AWS_STORAGE_BUCKET_NAME:-kotoku-local}"
ACCESS_KEY="${AWS_ACCESS_KEY_ID:-kotokuadmin}"
SECRET_KEY="${AWS_SECRET_ACCESS_KEY:-kotokuadmin123}"

echo "Waiting for MinIO at ${ENDPOINT}..."
python - <<'PY'
import os, time, urllib.request, urllib.error
endpoint = os.environ.get("AWS_ENDPOINT_URL_S3") or os.environ.get("AWS_S3_ENDPOINT_URL", "http://minio:9000")
for i in range(30):
    try:
        urllib.request.urlopen(f"{endpoint}/minio/health/live", timeout=2)
        print("MinIO is live.")
        break
    except (urllib.error.URLError, OSError):
        time.sleep(1)
else:
    raise RuntimeError("MinIO did not become healthy in 30s")
PY

python - <<PY
import boto3, json, os

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL_S3") or os.environ["AWS_S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)
bucket = os.environ["AWS_STORAGE_BUCKET_NAME"]
buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
if bucket not in buckets:
    s3.create_bucket(Bucket=bucket)
    print(f"Created bucket: {bucket}")
else:
    print(f"Bucket already exists: {bucket}")

policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetObject"],
        "Resource": [f"arn:aws:s3:::{bucket}/*"]
    }]
}
s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
print(f"Set public read policy on bucket: {bucket}")

cors_config = {
    "CORSRules": [
        {
            "AllowedOrigins": [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ],
            "AllowedMethods": ["PUT", "GET", "HEAD", "OPTIONS"],
            "AllowedHeaders": [
                "Content-Type",
                "x-amz-meta-sha256",
                "x-amz-*",
                "Authorization",
                "*",
            ],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 3600,
        }
    ]
}
s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_config)
print(f"Set CORS policy on bucket: {bucket}")
PY
