import hashlib
import hmac
import secrets
from datetime import timedelta

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


def generate_otp(length: int = 6) -> str:
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
    def verify_otp(*, consent_record_id: int, otp_code: str) -> ConsentRecord:
        try:
            record = ConsentRecord.objects.select_related("agreement").get(
                pk=consent_record_id
            )
        except ConsentRecord.DoesNotExist:
            raise DomainError("Consent record not found") from None
        if record.granted:
            raise DomainError("Consent already granted")
        if record.expires_at < timezone.now():
            raise DomainError("OTP has expired")
        if not verify_otp_hash(otp_code, record.otp_code_hash):
            raise DomainError("Invalid OTP code")
        record.granted = True
        record.granted_at = timezone.now()
        record.save(update_fields=["granted", "granted_at"])
        AuditService.record_event(
            event_type="consent.granted",
            entity_type="consent_record",
            entity_id=str(record.pk),
            metadata={"channel": record.channel},
        )
        agreement = record.agreement
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
