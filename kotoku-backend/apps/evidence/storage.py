import uuid

from apps.evidence.hashing import hash_bytes
from infrastructure.storage.s3 import S3StorageClient


def store_evidence(file_data: bytes, filename: str) -> tuple[str, str]:
    file_hash = hash_bytes(file_data)
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    key = f"evidence/{file_hash[:2]}/{file_hash}.{ext}"
    client = S3StorageClient()
    url = client.upload(key, file_data)
    return file_hash, url


def build_evidence_key(file_hash: str, ext: str) -> str:
    return f"evidence/{file_hash[:2]}/{uuid.uuid4().hex[:8]}_{file_hash[:12]}.{ext}"
