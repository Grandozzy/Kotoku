import logging
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.domain.policies import can_request_consent
from apps.agreements.domain.state_machine import next_state
from apps.agreements.models import Agreement, AgreementRevision
from apps.audit.services import AuditService
from apps.consent.models import ConsentRecord
from apps.evidence.models import EvidenceItem
from apps.notifications.tasks import send_arkesel_otp
from infrastructure.sms.arkesel_client import ArkeselOtpClient
from apps.parties.models import Party
from common.exceptions import DomainError, ServiceUnavailableError
from common.phone_numbers import normalize_phone_for_compare
from infrastructure.storage.s3 import S3StorageClient

logger = logging.getLogger(__name__)

_OTP_MAX_ATTEMPTS = 3
_OTP_LOCKOUT_SECONDS = 900  # 15 minutes
_CONSENT_LINK_SALT = "kotoku.consent-link.v1"


def _public_evidence_payload(item: EvidenceItem) -> dict:
    view_url = None
    if item.file_key:
        try:
            view_url = S3StorageClient().generate_presigned_view_url(
                item.file_key,
                content_type=item.mime_type,
                expires_in=settings.EVIDENCE_VIEW_URL_TTL_SECONDS,
            )
        except Exception:
            logger.exception(
                "Failed to generate public consent evidence view URL",
                extra={"evidence_id": item.pk, "agreement_id": item.agreement_id},
            )

    return {
        "id": item.pk,
        "evidence_type": item.evidence_type,
        "file_type": item.file_type,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "original_name": item.original_name,
        "upload_status": item.upload_status,
        "uploaded_by_role": item.uploaded_by.role if item.uploaded_by_id else None,
        "created_at": item.created_at,
        "view_url": view_url,
    }


def get_sms_gateway():
    """
    Compatibility wrapper for consent-flow tests and direct OTP issuance.

    Some integration tests patch this symbol to capture OTPs synchronously.
    """
    from apps.notifications.providers.sms_provider import SmsNotificationProvider  # noqa: PLC0415

    return SmsNotificationProvider()


# OTP generation, hashing, and verification delegated to Arkesel OTP API.


def _is_creator_party(*, agreement: Agreement, party: Party) -> bool:
    party_phone = normalize_phone_for_compare(party.phone)
    creator_user = getattr(agreement.created_by, "user", None)
    creator_phones = {
        normalize_phone_for_compare(agreement.created_by.phone),
        normalize_phone_for_compare(getattr(creator_user, "phone", "")),
    }
    creator_phones.discard("")
    if party_phone and party_phone in creator_phones:
        return True

    party_a_id = (
        Party.objects.filter(agreement=agreement)
        .order_by("id")
        .values_list("id", flat=True)
        .first()
    )
    return party.pk == party_a_id


def _get_party_by_phone(*, agreement_id: int, phone: str) -> Party:
    phone_key = normalize_phone_for_compare(phone)
    for party in Party.objects.filter(agreement_id=agreement_id):
        if normalize_phone_for_compare(party.phone) == phone_key:
            return party
    raise Party.DoesNotExist


def _enqueue_consent_otp_after_commit(
    *,
    agreement_id: int,
    party_id: int,
    number: str,
    message: str,
) -> None:
    def _send_otp() -> None:
        try:
            send_arkesel_otp.delay(number=number, message=message)
        except Exception as exc:
            logger.exception(
                "Failed to enqueue consent OTP via Arkesel",
                extra={
                    "agreement_id": agreement_id,
                    "party_id": party_id,
                    "sms_error": exc.__class__.__name__,
                },
            )
            raise ServiceUnavailableError(
                "Consent codes could not be sent right now. Please try again."
            ) from None

    transaction.on_commit(_send_otp)


class ConsentService:
    @staticmethod
    def make_consent_link_token(
        *,
        agreement_id: int,
        party_id: int,
        purpose: str = ConsentRecord.Purpose.CONSENT,
    ) -> str:
        return signing.dumps(
            {
                "agreement_id": agreement_id,
                "party_id": party_id,
                "purpose": purpose,
            },
            salt=_CONSENT_LINK_SALT,
        )

    @staticmethod
    def load_consent_link_token(token: str) -> dict:
        try:
            payload = signing.loads(
                token,
                salt=_CONSENT_LINK_SALT,
                max_age=settings.CONSENT_LINK_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            raise DomainError("Invalid or expired consent link.") from None
        if not isinstance(payload, dict):
            raise DomainError("Invalid or expired consent link.")
        return payload

    @staticmethod
    def _issue_party_otps(
        *,
        agreement: Agreement,
        parties: list[Party],
        purpose: str = ConsentRecord.Purpose.CONSENT,
        event_type: str = "consent.otp_issued",
        sms_label: str = "consent",
    ) -> list[ConsentRecord]:
        records = []
        for party in parties:
            # Arkesel generates and manages the OTP server-side.
            # otp_code_hash kept as empty string — field retained for schema compat.
            record = ConsentRecord.objects.create(
                agreement=agreement,
                party=party,
                purpose=purpose,
                otp_code_hash="",
                channel=ConsentRecord.Channel.SMS,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            phone = party.phone
            if phone:
                is_creator_party = (
                    purpose == ConsentRecord.Purpose.CONSENT
                    and _is_creator_party(agreement=agreement, party=party)
                )
                if purpose == ConsentRecord.Purpose.CONSENT and not is_creator_party:
                    token = ConsentService.make_consent_link_token(
                        agreement_id=agreement.pk,
                        party_id=party.pk,
                        purpose=purpose,
                    )
                    consent_url = f"{settings.KOTOKU_WEB_URL}/consent/{token}"
                    body = (
                        f"Your Kotoku {sms_label} code is %otp_code%. "
                        f"Review and confirm: {consent_url}. "
                        f"Valid for 10 minutes. Do not share this code."
                    )
                else:
                    body = (
                        f"Your Kotoku {sms_label} code is %otp_code%. "
                        f"Valid for 10 minutes. Do not share this code."
                    )
                _enqueue_consent_otp_after_commit(
                    agreement_id=agreement.pk,
                    party_id=party.pk,
                    number=phone,
                    message=body,
                )
            AuditService.record_event(
                event_type=event_type,
                entity_type="consent_record",
                entity_id=str(record.pk),
                actor=str(party.pk),
                metadata={"channel": ConsentRecord.Channel.SMS, "party_id": party.pk},
            )
            records.append(record)
        return records

    @staticmethod
    @transaction.atomic
    def request_consent(*, agreement_id: int) -> list[ConsentRecord]:
        agreement = Agreement.objects.select_related(
            "created_by",
            "created_by__user",
        ).get(pk=agreement_id)
        if agreement.status != AgreementStatus.PENDING_CONSENT:
            raise DomainError(
                "Cannot request consent: agreement must be in pending_consent status"
            )
        from apps.consent.selectors import ConsentSelector  # noqa: PLC0415

        existing_records = ConsentSelector.list_consent_for_agreement(
            agreement_id=agreement_id
        )
        if existing_records.exists() and ConsentSelector.all_parties_consented(
            agreement_id=agreement_id
        ):
            raise DomainError("All parties have already consented. Proceed to seal.")

        ConsentRecord.objects.filter(
            agreement=agreement,
            purpose=ConsentRecord.Purpose.CONSENT,
        ).delete()
        parties = list(Party.objects.filter(agreement=agreement).order_by("id"))
        if not parties:
            raise DomainError("Cannot request consent: agreement has no parties")
        return ConsentService._issue_party_otps(
            agreement=agreement,
            parties=parties,
            purpose=ConsentRecord.Purpose.CONSENT,
            event_type="consent.requested",
            sms_label="consent",
        )

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

        if record.granted:
            raise DomainError("Invalid or expired verification code")
        if record.expires_at < timezone.now():
            raise DomainError("Invalid or expired verification code")

        client = ArkeselOtpClient()
        phone = record.party.phone
        if not client.verify_otp(number=phone, code=otp_code):
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
        SMS is sent directly to party.phone so this works for parties created via
        the Parties API that may not yet have a linked Account.
        """
        agreement = (
            Agreement.objects.select_related("created_by", "created_by__user")
            .select_for_update()
            .get(pk=agreement_id)
        )

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

        ConsentRecord.objects.filter(
            agreement=agreement,
            purpose=ConsentRecord.Purpose.CONSENT,
        ).delete()

        parties = list(Party.objects.filter(agreement=agreement).order_by("id"))
        if not parties:
            raise DomainError("Cannot issue OTPs: agreement has no parties.")

        return ConsentService._issue_party_otps(
            agreement=agreement,
            parties=parties,
            purpose=ConsentRecord.Purpose.CONSENT,
            event_type="consent.otp_issued",
            sms_label="consent",
        )

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

        return ConsentService._issue_party_otps(
            agreement=agreement,
            parties=parties,
            purpose=ConsentRecord.Purpose.REOPEN,
            event_type="consent.reopen_otp_issued",
            sms_label="reopen",
        )

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
            party = _get_party_by_phone(agreement_id=agreement_id, phone=party_phone)
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

        if record.expires_at < timezone.now():
            raise DomainError("Invalid or expired verification code.")

        client = ArkeselOtpClient()
        if not client.verify_otp(number=party_phone, code=otp_code):
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
        *,
        agreement_id: int,
        party_phone: str,
        otp_code: str,
        purpose: str = ConsentRecord.Purpose.CONSENT,
    ) -> ConsentRecord:
        """Verify a party's consent OTP identified by their phone number.

        Rate-limited to _OTP_MAX_ATTEMPTS attempts per consent record with a
        _OTP_LOCKOUT_SECONDS lockout, matching the existing verify_otp() behaviour.
        Errors are intentionally unified to avoid leaking record state.
        """
        try:
            party = _get_party_by_phone(agreement_id=agreement_id, phone=party_phone)
        except Party.DoesNotExist:
            raise DomainError("Invalid or expired verification code.") from None

        try:
            record = (
                ConsentRecord.objects.select_for_update()
                .get(
                    agreement_id=agreement_id,
                    party=party,
                    purpose=purpose,
                    granted=False,
                )
            )
        except ConsentRecord.DoesNotExist:
            raise DomainError("Invalid or expired verification code.") from None

        cache_key = f"otp_attempts:{record.pk}"
        attempts = cache.get(cache_key, 0)
        if attempts >= _OTP_MAX_ATTEMPTS:
            raise DomainError("Too many verification attempts. Try again later.")

        if record.expires_at < timezone.now():
            raise DomainError("Invalid or expired verification code.")

        client = ArkeselOtpClient()
        if not client.verify_otp(number=party_phone, code=otp_code):
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
        from apps.consent.selectors import ConsentSelector  # noqa: PLC0415
        if (
            purpose == ConsentRecord.Purpose.CONSENT
            and ConsentSelector.all_parties_consented(
                agreement_id=agreement_id,
                purpose=purpose,
            )
        ):
            agreement = Agreement.objects.select_for_update().get(pk=agreement_id)
            has_revision = AgreementRevision.objects.filter(
                agreement=agreement
            ).exists()
            if not has_revision:
                agreement.status = next_state(agreement.status, "all_consented")
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

    @staticmethod
    def get_public_consent_context(*, token: str) -> dict:
        payload = ConsentService.load_consent_link_token(token)
        agreement_id = int(payload.get("agreement_id") or 0)
        party_id = int(payload.get("party_id") or 0)
        purpose = payload.get("purpose") or ConsentRecord.Purpose.CONSENT

        try:
            party = Party.objects.select_related("agreement").get(
                pk=party_id,
                agreement_id=agreement_id,
            )
        except Party.DoesNotExist:
            raise DomainError("Invalid or expired consent link.") from None

        agreement = party.agreement
        parties = list(Party.objects.filter(agreement=agreement).order_by("id"))
        evidence = [
            _public_evidence_payload(item)
            for item in EvidenceItem.objects.filter(
                agreement=agreement,
                upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            )
            .select_related("uploaded_by")
            .order_by("-created_at")
        ]
        record = (
            ConsentRecord.objects.filter(
                agreement=agreement,
                party=party,
                purpose=purpose,
            )
            .order_by("-created_at")
            .first()
        )
        from apps.consent.selectors import ConsentSelector  # noqa: PLC0415
        all_consented = ConsentSelector.all_parties_consented(
            agreement_id=agreement.pk,
            purpose=purpose,
        )

        return {
            "agreement": {
                "id": agreement.pk,
                "title": agreement.title,
                "scenario_template": agreement.scenario_template,
                "status": agreement.status,
                "field_data": agreement.field_data,
            },
            "party": {
                "id": party.pk,
                "role": party.role,
                "display_name": party.display_name,
                "phone": party.phone,
            },
            "parties": [
                {
                    "id": item.pk,
                    "role": item.role,
                    "display_name": item.display_name,
                    "phone": item.phone,
                }
                for item in parties
            ],
            "evidence": evidence,
            "consent_record": record,
            "all_consented": all_consented,
        }

    @staticmethod
    @transaction.atomic
    def confirm_public_link(*, token: str, otp_code: str) -> dict:
        context = ConsentService.get_public_consent_context(token=token)
        party = context["party"]
        record = ConsentService.confirm_by_phone(
            agreement_id=context["agreement"]["id"],
            party_phone=party["phone"],
            otp_code=otp_code,
            purpose=ConsentRecord.Purpose.CONSENT,
        )
        all_consented = not ConsentRecord.objects.filter(
            agreement_id=context["agreement"]["id"],
            purpose=ConsentRecord.Purpose.CONSENT,
            granted=False,
        ).exists()
        return {"consent_record": record, "all_consented": all_consented}
