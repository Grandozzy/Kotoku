import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement
from apps.audit.services import AuditService
from apps.consent.models import ConsentRecord
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.parties.models import Party
from common.exceptions import DomainError

logger = logging.getLogger(__name__)

_OTP_MAX_ATTEMPTS = 3
_OTP_LOCKOUT_SECONDS = 900  # 15 minutes


def generate_otp(length: int = 8) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp_code: str) -> str:
    return hashlib.sha256(otp_code.encode()).hexdigest()


def verify_otp_hash(otp_code: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(otp_code), otp_hash)


def generate_otp_expiry(minutes: int = 10) -> timezone.datetime:
    return timezone.now() + timedelta(minutes=minutes)


class ConsentService:
    @staticmethod
    def request_consent(*, agreement_id: int) -> list[ConsentRecord]:
        agreement = Agreement.objects.get(pk=agreement_id)
        if agreement.status != AgreementStatus.PENDING_CONSENT:
            raise DomainError(
                "Cannot request consent: agreement must be in pending_consent status"
            )
        parties = list(
            Party.objects.filter(agreement=agreement).select_related(
                "identity__account"
            )
        )
        if not parties:
            raise DomainError("Cannot request consent: agreement has no parties")
        records = []
        for party in parties:
            otp_code = generate_otp()
            record = ConsentRecord.objects.create(
                agreement=agreement,
                party=party,
                otp_code_hash=hash_otp(otp_code),
                channel=ConsentRecord.Channel.SMS,
                expires_at=generate_otp_expiry(),
            )
            NotificationService.send_notification(
                account_id=party.identity.account.pk,
                channel=Notification.Channel.SMS,
                body=f"Your verification code is {otp_code}. It expires in 10 minutes.",
            )
            AuditService.record_event(
                event_type="consent.requested",
                entity_type="consent_record",
                entity_id=str(record.pk),
                actor=str(party.pk),
                metadata={"channel": ConsentRecord.Channel.SMS},
            )
            records.append(record)
        return records

    @staticmethod
    @transaction.atomic
    def verify_otp(*, consent_record_id: int, otp_code: str) -> ConsentRecord:
        cache_key = f"otp_attempts:{consent_record_id}"
        attempts = cache.get(cache_key, 0)
        if attempts >= _OTP_MAX_ATTEMPTS:
            raise DomainError("Too many verification attempts. Try again later.")

        try:
            record = ConsentRecord.objects.select_related("agreement").select_for_update().get(
                pk=consent_record_id
            )
        except ConsentRecord.DoesNotExist:
            raise DomainError("Invalid or expired verification code") from None

        # Validate all conditions before revealing which one failed, to avoid
        # leaking whether the record exists, is already granted, or has expired.
        valid = (
            not record.granted
            and record.expires_at >= timezone.now()
            and verify_otp_hash(otp_code, record.otp_code_hash)
        )
        if not valid:
            cache.set(cache_key, attempts + 1, timeout=_OTP_LOCKOUT_SECONDS)
            logger.warning(
                "Failed OTP verification for consent_record=%s (attempt %s)",
                consent_record_id,
                attempts + 1,
            )
            raise DomainError("Invalid or expired verification code")

        cache.delete(cache_key)
        record.granted = True
        record.granted_at = timezone.now()
        record.save(update_fields=["granted", "granted_at"])
        AuditService.record_event(
            event_type="consent.granted",
            entity_type="consent_record",
            entity_id=str(record.pk),
            metadata={"channel": record.channel},
        )
        agreement = Agreement.objects.select_for_update().get(pk=record.agreement_id)
        all_granted = not ConsentRecord.objects.filter(
            agreement=agreement, granted=False
        ).exists()
        if all_granted:
            new_status = next_state(agreement.status, "all_consented")
            agreement.status = new_status
            agreement.save(update_fields=["status", "updated_at"])
            AuditService.record_event(
                event_type="agreement.all_consented",
                entity_type="agreement",
                entity_id=str(agreement.pk),
            )
        return record
