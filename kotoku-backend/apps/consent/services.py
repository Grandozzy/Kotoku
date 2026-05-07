import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.policies import can_request_consent
from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement, AgreementRevision
from apps.audit.services import AuditService
from apps.consent.models import ConsentRecord
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.parties.models import Party
from common.exceptions import DomainError
from infrastructure.sms import get_sms_gateway

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
            has_revision = AgreementRevision.objects.filter(
                agreement=agreement
            ).exists()
            if not has_revision:
                new_status = next_state(agreement.status, "all_consented")
                agreement.status = new_status
                agreement.save(update_fields=["status", "updated_at"])
                AuditService.record_event(
                    event_type="agreement.all_consented",
                    entity_type="agreement",
                    entity_id=str(agreement.pk),
                )
            else:
                AuditService.record_event(
                    event_type="agreement.reseal_all_consented",
                    entity_type="agreement",
                    entity_id=str(agreement.pk),
                )
        return record

    # ------------------------------------------------------------------ #
    # New API flow: phone-based OTP request and confirmation.             #
    # ------------------------------------------------------------------ #

    @staticmethod
    @transaction.atomic
    def request_otp(*, agreement_id: int) -> list[ConsentRecord]:
        """Transition the agreement to PENDING_CONSENT and issue OTPs to all parties.

        Accepted from DRAFT (first call) or PENDING_CONSENT (re-issue after expiry).
        SMS is sent directly to party.phone via SmsGateway so this works for parties
        created via the Parties API that may not yet have a linked Account.
        """
        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)

        if not can_request_consent(agreement):
            raise DomainError(
                "Agreement must have at least 2 parties and be in draft or "
                "pending_consent status."
            )

        original_status = agreement.status

        from apps.consent.selectors import ConsentSelector  # noqa: PLC0415
        if agreement.status == AgreementStatus.PENDING_CONSENT:
            if ConsentSelector.all_parties_consented(agreement_id=agreement_id):
                raise DomainError(
                    "All parties have already consented. Proceed to seal."
                )
            # Re-issue: wipe stale records so each party gets a fresh OTP.
            ConsentRecord.objects.filter(agreement=agreement).delete()
        else:
            # DRAFT or ACTIVE → PENDING_CONSENT
            agreement.status = next_state(agreement.status, "request_consent")
            agreement.save(update_fields=["status", "updated_at"])
            event_type = (
                "agreement.reseal_consent_requested"
                if original_status == AgreementStatus.ACTIVE
                else "agreement.consent_requested"
            )
            AuditService.record_event(
                event_type=event_type,
                entity_type="agreement",
                entity_id=str(agreement.pk),
            )

        parties = list(Party.objects.filter(agreement=agreement))
        if not parties:
            raise DomainError("Cannot issue OTPs: agreement has no parties.")

        gateway = get_sms_gateway()
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
            phone = party.phone
            if phone:
                try:
                    gateway.send(
                        to=phone,
                        body=(
                            f"Your Kotoku consent code is {otp_code}. "
                            f"Valid for 10 minutes. Do not share this code."
                        ),
                    )
                except Exception:
                    logger.exception(
                        "Failed to send consent OTP SMS to party %s", party.pk
                    )
            AuditService.record_event(
                event_type="consent.otp_issued",
                entity_type="consent_record",
                entity_id=str(record.pk),
                actor=str(party.pk),
                metadata={"channel": ConsentRecord.Channel.SMS, "party_id": party.pk},
            )
            records.append(record)
        return records

    # ------------------------------------------------------------------ #
    # Reopen-consent OTP flow (bilateral re-auth for Sprint 6).          #
    # ------------------------------------------------------------------ #

    @staticmethod
    @transaction.atomic
    def request_reopen_otp(*, agreement_id: int) -> list[ConsentRecord]:
        """Issue reopen-consent OTPs to all parties on a REOPEN_REQUESTED agreement.

        Any existing ungranted reopen-consent records are wiped first so
        each call starts fresh (re-issue after expiry).
        """
        from apps.agreements.domain.enums import AgreementStatus  # noqa: PLC0415
        from apps.agreements.models import Agreement  # noqa: PLC0415

        agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
        if agreement.status != AgreementStatus.REOPEN_REQUESTED:
            raise DomainError(
                "Reopen OTPs can only be issued for agreements in reopen_requested status."
            )

        # Wipe stale ungranted reopen-consent records.
        ConsentRecord.objects.filter(
            agreement=agreement,
            purpose=ConsentRecord.Purpose.REOPEN,
            granted=False,
        ).delete()

        parties = list(Party.objects.filter(agreement=agreement))
        if not parties:
            raise DomainError("Cannot issue reopen OTPs: agreement has no parties.")

        gateway = get_sms_gateway()
        records = []
        for party in parties:
            otp_code = generate_otp()
            record = ConsentRecord.objects.create(
                agreement=agreement,
                party=party,
                purpose=ConsentRecord.Purpose.REOPEN,
                otp_code_hash=hash_otp(otp_code),
                channel=ConsentRecord.Channel.SMS,
                expires_at=generate_otp_expiry(),
            )
            phone = party.phone
            if phone:
                try:
                    gateway.send(
                        to=phone,
                        body=(
                            f"Your Kotoku reopen code is {otp_code}. "
                            f"Valid for 10 minutes. Do not share this code."
                        ),
                    )
                except Exception:
                    logger.exception(
                        "Failed to send reopen OTP SMS to party %s", party.pk
                    )
            AuditService.record_event(
                event_type="consent.reopen_otp_issued",
                entity_type="consent_record",
                entity_id=str(record.pk),
                actor=str(party.pk),
                metadata={"channel": ConsentRecord.Channel.SMS, "party_id": party.pk},
            )
            records.append(record)
        return records

    @staticmethod
    @transaction.atomic
    def confirm_reopen_by_phone(
        *, agreement_id: int, party_phone: str, otp_code: str
    ) -> ConsentRecord:
        """Verify a party's reopen-consent OTP identified by their phone number.

        When all parties have confirmed, this triggers the bilateral_confirm
        state transition (REOPEN_REQUESTED → ACTIVE) via AgreementService.
        """
        try:
            party = Party.objects.get(agreement_id=agreement_id, phone=party_phone)
        except Party.DoesNotExist:
            raise DomainError("Invalid or expired verification code.") from None

        try:
            record = ConsentRecord.objects.select_for_update().get(
                agreement_id=agreement_id,
                party=party,
                purpose=ConsentRecord.Purpose.REOPEN,
                granted=False,
            )
        except ConsentRecord.DoesNotExist:
            raise DomainError("Invalid or expired verification code.") from None

        cache_key = f"reopen_otp_attempts:{record.pk}"
        attempts = cache.get(cache_key, 0)
        if attempts >= _OTP_MAX_ATTEMPTS:
            raise DomainError("Too many verification attempts. Try again later.")

        valid = (
            record.expires_at >= timezone.now()
            and verify_otp_hash(otp_code, record.otp_code_hash)
        )
        if not valid:
            cache.set(cache_key, attempts + 1, timeout=_OTP_LOCKOUT_SECONDS)
            logger.warning(
                "Failed reopen OTP for party phone=%s agreement=%s (attempt %s)",
                party_phone, agreement_id, attempts + 1,
            )
            raise DomainError("Invalid or expired verification code.")

        cache.delete(cache_key)
        record.granted = True
        record.granted_at = timezone.now()
        record.save(update_fields=["granted", "granted_at"])

        AuditService.record_event(
            event_type="consent.reopen_granted",
            entity_type="consent_record",
            entity_id=str(record.pk),
            metadata={"party_id": party.pk, "channel": record.channel},
        )

        # Check if all parties have now confirmed; if so, complete the reopen.
        from apps.agreements.domain.policies import all_parties_confirmed_reopen  # noqa: PLC0415
        if all_parties_confirmed_reopen(agreement_id):
            from apps.agreements.services import AgreementService  # noqa: PLC0415
            AgreementService.complete_bilateral_reopen(agreement_id=agreement_id)

        return record

    @staticmethod
    @transaction.atomic
    def confirm_by_phone(
        *, agreement_id: int, party_phone: str, otp_code: str
    ) -> ConsentRecord:
        """Verify a party's consent OTP identified by their phone number.

        Rate-limited to _OTP_MAX_ATTEMPTS attempts per consent record with a
        _OTP_LOCKOUT_SECONDS lockout, matching the existing verify_otp() behaviour.
        Errors are intentionally unified to avoid leaking record state.
        """
        try:
            party = Party.objects.get(agreement_id=agreement_id, phone=party_phone)
        except Party.DoesNotExist:
            raise DomainError("Invalid or expired verification code.") from None

        try:
            record = (
                ConsentRecord.objects.select_for_update()
                .get(agreement_id=agreement_id, party=party, granted=False)
            )
        except ConsentRecord.DoesNotExist:
            raise DomainError("Invalid or expired verification code.") from None

        cache_key = f"otp_attempts:{record.pk}"
        attempts = cache.get(cache_key, 0)
        if attempts >= _OTP_MAX_ATTEMPTS:
            raise DomainError("Too many verification attempts. Try again later.")

        valid = (
            record.expires_at >= timezone.now()
            and verify_otp_hash(otp_code, record.otp_code_hash)
        )
        if not valid:
            cache.set(cache_key, attempts + 1, timeout=_OTP_LOCKOUT_SECONDS)
            logger.warning(
                "Failed consent OTP for party phone=%s agreement=%s (attempt %s)",
                party_phone, agreement_id, attempts + 1,
            )
            raise DomainError("Invalid or expired verification code.")

        cache.delete(cache_key)
        record.granted = True
        record.granted_at = timezone.now()
        record.save(update_fields=["granted", "granted_at"])

        AuditService.record_event(
            event_type="consent.granted",
            entity_type="consent_record",
            entity_id=str(record.pk),
            metadata={"party_id": party.pk, "channel": record.channel},
        )
        return record
