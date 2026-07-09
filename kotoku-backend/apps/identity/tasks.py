from celery import shared_task

from common.exceptions import ServiceUnavailableError
from apps.identity.services import IdentityService


@shared_task(
    bind=True,
    autoretry_for=(ServiceUnavailableError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    name="apps.identity.tasks.verify_party_identity",
)
def verify_party_identity(self, party_id: int):
    return IdentityService.verify_party_identity(
        party_id=party_id,
        soft_fail_unavailable=False,
    )
