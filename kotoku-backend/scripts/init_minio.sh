#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${AWS_S3_ENDPOINT_URL:-http://minio:9000}"
BUCKET="${AWS_STORAGE_BUCKET_NAME:-kotoku-local}"
ACCESS_KEY="${AWS_ACCESS_KEY_ID:-kotokuadmin}"
SECRET_KEY="${AWS_SECRET_ACCESS_KEY:-kotokuadmin123}"

echo "Waiting for MinIO at ${ENDPOINT}..."
for i in $(seq 1 30); do
  if curl -sf "${ENDPOINT}/minio/health/live" >/dev/null 2>&1; then
    echo "MinIO is live."
    break
  fi
  sleep 1
done

python - <<PY
import boto3, os

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["AWS_S3_ENDPOINT_URL"],
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
PY
