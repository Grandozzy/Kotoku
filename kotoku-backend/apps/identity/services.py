import re
from dataclasses import dataclass
import logging

from django.db import transaction
from django.utils import timezone

from apps.identity.models import IdentityRecord, PartyIdentityVerification
from apps.parties.identity import latest_identity_evidence_by_party, normalize_ghana_card_pin
from common.exceptions import DomainError, ServiceUnavailableError
from infrastructure.google_vision.client import GoogleVisionClient
from infrastructure.rekognition.client import RekognitionClient
from infrastructure.storage.s3 import S3StorageClient

_OCR_PIN_RE = re.compile(r"GHA[\s-]*(\d{9})[\s-]*(\d)")
logger = logging.getLogger("kotoku")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.upper()).strip()


def _normalize_name_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^A-Z0-9]+", value.upper()) if len(token) >= 2]


def _extract_ocr_pin(text: str) -> str:
    match = _OCR_PIN_RE.search(_normalize_text(text))
    if not match:
        return ""
    return f"GHA-{match.group(1)}-{match.group(2)}"


def _has_ghana_card_markers(front_text: str, back_text: str) -> bool:
    combined = _normalize_text(f"{front_text} {back_text}")
    has_ghana = "GHANA" in combined
    has_identity_marker = any(
        marker in combined
        for marker in (
            "NATIONAL IDENTITY CARD",
            "NATIONAL IDENTIFICATION",
            "IDENTIFICATION AUTHORITY",
            "IDENTITY CARD",
        )
    )
    return has_ghana and has_identity_marker


def _name_matches(front_text: str, entered_name: str) -> bool:
    tokens = _normalize_name_tokens(entered_name)
    if not tokens:
        return False
    normalized_front = _normalize_text(front_text)
    return all(token in normalized_front for token in tokens)


def _extract_ocr_name(front_text: str, entered_name: str) -> str:
    tokens = _normalize_name_tokens(entered_name)
    normalized_front = _normalize_text(front_text)
    matched = [token for token in tokens if token in normalized_front]
    return " ".join(matched)


@dataclass(frozen=True)
class IdentityVerificationOutcome:
    status: str
    detail: str
    failure_codes: list[str]
    ocr_pin: str
    ocr_full_name: str
    front_text: str
    back_text: str
    front_evidence_id: int | None
    back_evidence_id: int | None
    selfie_evidence_id: int | None
    face_match_score: float | None


class IdentityService:
    @staticmethod
    def create_identity_record(*, account, reference: str, verification_type: str):
        reference = reference.strip()
        if not reference:
            raise ValueError("Identity reference cannot be empty.")
        return IdentityRecord.objects.create(
            account=account,
            reference=reference,
            verification_type=verification_type,
        )

    @staticmethod
    def mark_verified(*, identity_record):
        identity_record.verified_at = timezone.now()
        identity_record.save(update_fields=["verified_at"])
        return identity_record

    @staticmethod
    def ensure_party_verification(*, party) -> PartyIdentityVerification:
        verification, _ = PartyIdentityVerification.objects.get_or_create(
            party=party,
            defaults={
                "entered_pin": normalize_ghana_card_pin(party.id_number or ""),
                "entered_full_name": party.display_name,
                "detail": "Awaiting Ghana Card verification.",
            },
        )
        return verification

    @staticmethod
    def reset_party_verification(*, party, detail: str = "Awaiting Ghana Card verification.") -> None:
        verification = IdentityService.ensure_party_verification(party=party)
        verification.status = PartyIdentityVerification.Status.PENDING
        verification.entered_pin = normalize_ghana_card_pin(party.id_number or "")
        verification.entered_full_name = party.display_name
        verification.ocr_pin = ""
        verification.ocr_full_name = ""
        verification.front_evidence_id = None
        verification.back_evidence_id = None
        verification.selfie_evidence_id = None
        verification.front_text = ""
        verification.back_text = ""
        verification.face_match_score = None
        verification.failure_codes = []
        verification.detail = detail
        verification.verified_at = None
        verification.save(
            update_fields=[
                "status",
                "entered_pin",
                "entered_full_name",
                "ocr_pin",
                "ocr_full_name",
                "front_evidence_id",
                "back_evidence_id",
                "selfie_evidence_id",
                "front_text",
                "back_text",
                "face_match_score",
                "failure_codes",
                "detail",
                "verified_at",
                "updated_at",
            ]
        )

    @staticmethod
    def queue_party_verification(*, party_id: int) -> None:
        from apps.identity.tasks import verify_party_identity

        def enqueue() -> None:
            try:
                verify_party_identity.delay(party_id)
            except Exception:
                logger.exception(
                    "[IDENTITY] queue_verification_failed party_id=%s falling_back_to_sync",
                    party_id,
                )
                try:
                    IdentityService.verify_party_identity(
                        party_id=party_id,
                        soft_fail_unavailable=True,
                    )
                except Exception:
                    logger.exception(
                        "[IDENTITY] sync_fallback_verification_failed party_id=%s",
                        party_id,
                    )

        transaction.on_commit(enqueue)

    @staticmethod
    @transaction.atomic
    def verify_party_identity(
        *,
        party_id: int,
        soft_fail_unavailable: bool = False,
    ) -> PartyIdentityVerification:
        from apps.parties.models import Party

        party = Party.objects.select_related("agreement").select_for_update().get(pk=party_id)
        verification = IdentityService.ensure_party_verification(party=party)
        evidence_by_party = latest_identity_evidence_by_party(
            parties=[party],
            evidence_items=party.agreement.evidence_items.all(),
        )
        role_items = evidence_by_party.get(party.role, {})
        front = role_items.get("front")
        back = role_items.get("back")
        selfie = role_items.get("selfie")

        if not front or not back or not selfie:
            verification.status = PartyIdentityVerification.Status.PENDING
            verification.detail = "Upload the Ghana Card front, back, and a selfie photo to start verification."
            verification.failure_codes = []
            verification.front_evidence_id = front.pk if front else None
            verification.back_evidence_id = back.pk if back else None
            verification.selfie_evidence_id = selfie.pk if selfie else None
            verification.face_match_score = None
            verification.verified_at = None
            verification.save(
                update_fields=[
                    "status",
                    "detail",
                    "failure_codes",
                    "front_evidence_id",
                    "back_evidence_id",
                    "selfie_evidence_id",
                    "face_match_score",
                    "verified_at",
                    "updated_at",
                ]
            )
            return verification

        verification.status = PartyIdentityVerification.Status.PROCESSING
        verification.entered_pin = normalize_ghana_card_pin(party.id_number or "")
        verification.entered_full_name = party.display_name
        verification.front_evidence_id = front.pk
        verification.back_evidence_id = back.pk
        verification.selfie_evidence_id = selfie.pk
        verification.detail = "Verifying Ghana Card details."
        verification.failure_codes = []
        verification.face_match_score = None
        verification.verified_at = None
        verification.save(
            update_fields=[
                "status",
                "entered_pin",
                "entered_full_name",
                "front_evidence_id",
                "back_evidence_id",
                "selfie_evidence_id",
                "detail",
                "failure_codes",
                "face_match_score",
                "verified_at",
                "updated_at",
            ]
        )

        try:
            outcome = IdentityService._run_ocr_verification(
                party=party,
                front_key=front.file_key,
                back_key=back.file_key,
                selfie_key=selfie.file_key,
                front_evidence_id=front.pk,
                back_evidence_id=back.pk,
                selfie_evidence_id=selfie.pk,
            )
        except ServiceUnavailableError:
            if not soft_fail_unavailable:
                raise
            outcome = IdentityVerificationOutcome(
                status=PartyIdentityVerification.Status.PENDING,
                detail="Identity verification is temporarily unavailable. We will retry automatically.",
                failure_codes=["verification_unavailable"],
                ocr_pin="",
                ocr_full_name="",
                front_text="",
                back_text="",
                front_evidence_id=front.pk,
                back_evidence_id=back.pk,
                selfie_evidence_id=selfie.pk,
                face_match_score=None,
            )
        except Exception:
            logger.exception("[IDENTITY] verification_unexpected_failure party_id=%s", party_id)
            outcome = IdentityVerificationOutcome(
                status=PartyIdentityVerification.Status.FAILED,
                detail="Identity verification failed unexpectedly. Please retry the Ghana Card upload.",
                failure_codes=["verification_unexpected_failure"],
                ocr_pin="",
                ocr_full_name="",
                front_text="",
                back_text="",
                front_evidence_id=front.pk,
                back_evidence_id=back.pk,
                selfie_evidence_id=selfie.pk,
                face_match_score=None,
            )

        verification.status = outcome.status
        verification.ocr_pin = outcome.ocr_pin
        verification.ocr_full_name = outcome.ocr_full_name
        verification.front_text = outcome.front_text
        verification.back_text = outcome.back_text
        verification.front_evidence_id = outcome.front_evidence_id
        verification.back_evidence_id = outcome.back_evidence_id
        verification.selfie_evidence_id = outcome.selfie_evidence_id
        verification.face_match_score = outcome.face_match_score
        verification.failure_codes = outcome.failure_codes
        verification.detail = outcome.detail
        verification.verified_at = (
            timezone.now()
            if outcome.status == PartyIdentityVerification.Status.VERIFIED
            else None
        )
        verification.save(
            update_fields=[
                "status",
                "ocr_pin",
                "ocr_full_name",
                "front_text",
                "back_text",
                "front_evidence_id",
                "back_evidence_id",
                "selfie_evidence_id",
                "face_match_score",
                "failure_codes",
                "detail",
                "verified_at",
                "updated_at",
            ]
        )
        return verification

    @staticmethod
    def _run_ocr_verification(
        *,
        party,
        front_key: str,
        back_key: str,
        selfie_key: str,
        front_evidence_id: int,
        back_evidence_id: int,
        selfie_evidence_id: int,
    ) -> IdentityVerificationOutcome:
        if not front_key or not back_key or not selfie_key:
            raise DomainError("Ghana Card images and selfie are required before verification.")

        storage = S3StorageClient()
        vision = GoogleVisionClient()
        rekognition = RekognitionClient()
        front_bytes = storage.get_object_bytes(front_key)
        back_bytes = storage.get_object_bytes(back_key)
        selfie_bytes = storage.get_object_bytes(selfie_key)
        front_text = vision.extract_document_text(front_bytes)
        back_text = vision.extract_document_text(back_bytes)
        ocr_pin = _extract_ocr_pin(f"{front_text}\n{back_text}")
        ocr_name = _extract_ocr_name(front_text, party.display_name)
        failure_codes: list[str] = []

        if not _has_ghana_card_markers(front_text, back_text):
            failure_codes.append("ghana_card_markers_missing")
        entered_pin = normalize_ghana_card_pin(party.id_number or "")
        if not ocr_pin:
            failure_codes.append("ocr_pin_missing")
        elif ocr_pin != entered_pin:
            failure_codes.append("ocr_pin_mismatch")
        if not _name_matches(front_text, party.display_name):
            failure_codes.append("ocr_name_mismatch")

        face_result = rekognition.compare_faces(
            source_bytes=selfie_bytes,
            target_bytes=front_bytes,
            similarity_threshold=70.0,
        )
        face_match_score = face_result["similarity"]
        if face_result["source_face_confidence"] <= 0:
            failure_codes.append("selfie_face_missing")
        elif face_match_score < 80:
            failure_codes.append("face_match_failed")
        elif face_match_score < 90:
            failure_codes.append("face_match_manual_review")

        if failure_codes:
            manual_review_only = failure_codes == ["face_match_manual_review"]
            return IdentityVerificationOutcome(
                status=(
                    PartyIdentityVerification.Status.MANUAL_REVIEW_REQUIRED
                    if manual_review_only
                    else PartyIdentityVerification.Status.FAILED
                ),
                detail=(
                    "Identity verification needs manual review."
                    if manual_review_only
                    else "Ghana Card verification failed. Upload a clearer card image and selfie that match the entered details."
                ),
                failure_codes=failure_codes,
                ocr_pin=ocr_pin,
                ocr_full_name=ocr_name,
                front_text="",
                back_text="",
                front_evidence_id=front_evidence_id,
                back_evidence_id=back_evidence_id,
                selfie_evidence_id=selfie_evidence_id,
                face_match_score=face_match_score,
            )

        return IdentityVerificationOutcome(
            status=PartyIdentityVerification.Status.VERIFIED,
            detail="Ghana Card and selfie verified.",
            failure_codes=[],
            ocr_pin=ocr_pin,
            ocr_full_name=ocr_name,
            front_text="",
            back_text="",
            front_evidence_id=front_evidence_id,
            back_evidence_id=back_evidence_id,
            selfie_evidence_id=selfie_evidence_id,
            face_match_score=face_match_score,
        )
