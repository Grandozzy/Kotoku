import logging

from celery import shared_task

from apps.identity.services import IdentityService
from common.exceptions import ServiceUnavailableError

logger = logging.getLogger("kotoku")


@shared_task(
    bind=True,
    autoretry_for=(ServiceUnavailableError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    name="apps.identity.tasks.verify_party_identity",
)
def verify_party_identity(self, party_id: int):
    logger.info("[IDENTITY] verify_party_identity task started party_id=%s", party_id)
    result = IdentityService.verify_party_identity(
        party_id=party_id,
        soft_fail_unavailable=False,
    )
    logger.info(
        "[IDENTITY] verify_party_identity task finished party_id=%s status=%s failure_codes=%s",
        party_id,
        result.status,
        list(result.failure_codes),
    )
    return result
