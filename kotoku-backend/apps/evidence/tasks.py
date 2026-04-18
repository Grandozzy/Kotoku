from celery import shared_task

from apps.evidence.models import EvidenceItem
from common.exceptions import DomainError


@shared_task
def process_evidence_upload(evidence_id: int) -> None:
    try:
        item = EvidenceItem.objects.get(pk=evidence_id)
    except EvidenceItem.DoesNotExist:
        return

    if not item.storage_url:
        raise DomainError("Evidence item has no stored file to verify")

    from infrastructure.storage.s3 import S3StorageClient

    client = S3StorageClient()
    key = item.storage_url.split(".amazonaws.com/", 1)[-1]
    client.generate_presigned_url(key)
    item.save(update_fields=[])
