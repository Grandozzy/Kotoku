import logging
import re

from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.evidence.api.serializers import (
    ConfirmUploadSerializer,
    EvidenceItemSerializer,
    UploadUrlRequestSerializer,
)
from apps.evidence.selectors import EvidenceSelector
from apps.evidence.services import EvidenceService
from common.phone_numbers import normalize_phone_for_compare
from common.responses import ok

logger = logging.getLogger("kotoku")

# Matches identity evidence types a non-owner party may upload for their own slot.
_PARTY_IDENTITY_PATTERN = re.compile(
    r"^(buyer|seller|landlord|tenant)_ghana_card_(front|back)$"
)


def _get_agreement_for_evidence_upload(
    agreement_id: int, account, evidence_type: str
) -> Agreement:
    """Return the agreement if the account is allowed to upload this evidence type.

    Owners may upload any evidence. Non-owners may upload only their own party's
    Ghana Card images (front/back) — the explicitly designed participant-upload
    flow for identity verification (see Section 16 of impl rules).
    """
    # Owner path — fast and covers all evidence types.
    try:
        return AgreementSelector.get_owned_agreement_detail(
            agreement_id, account_id=account.pk
        )
    except Agreement.DoesNotExist:
        pass

    # Non-owner: restrict to identity evidence for their own party slot only.
    if not _PARTY_IDENTITY_PATTERN.match(evidence_type or ""):
        raise Http404

    role = evidence_type.split("_ghana_card_")[0]

    try:
        from apps.parties.models import Party

        party = Party.objects.select_related("agreement").get(
            agreement_id=agreement_id, role=role
        )
    except Exception:
        raise Http404 from None

    if normalize_phone_for_compare(party.phone) != normalize_phone_for_compare(account.phone):
        raise Http404

    return party.agreement


class EvidenceUploadUrlView(APIView):
    """POST /api/agreements/{id}/evidence/upload-url

    Issue a presigned PUT URL so the client can upload directly to object storage.
    Owners may upload any evidence type. Non-owners may upload only their own party's
    Ghana Card images (front/back) for the identity invite flow.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int):
        serializer = UploadUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence_type = serializer.validated_data["evidence_type"]

        _get_agreement_for_evidence_upload(agreement_id, request.user.account, evidence_type)

        logger.info(
            "[EVIDENCE] generate_upload_url agreement=%s evidence_type=%s account=%s",
            agreement_id,
            evidence_type,
            request.user.account.pk,
        )
        result = EvidenceService.generate_upload_url(
            agreement_id=agreement_id,
            uploading_account=request.user.account,
            **serializer.validated_data,
        )
        logger.info(
            "[EVIDENCE] upload_url issued agreement=%s evidence_id=%s",
            agreement_id,
            result["evidence_id"],
        )
        return ok(result, status_code=201)


class EvidenceCollectionView(APIView):
    """POST   /api/agreements/{id}/evidence  — confirm upload and record metadata
       GET    /api/agreements/{id}/evidence  — list confirmed evidence items
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_visible_agreement(
        self, agreement_id: int, account_id: int, account_phone: str
    ):
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=account_id,
                account_phone=account_phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def post(self, request, agreement_id: int):
        serializer = ConfirmUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence_type = serializer.validated_data["evidence_type"]

        _get_agreement_for_evidence_upload(agreement_id, request.user.account, evidence_type)

        logger.info(
            "[EVIDENCE] confirm_upload agreement=%s evidence_type=%s",
            agreement_id,
            evidence_type,
        )
        item = EvidenceService.confirm_upload(
            agreement_id=agreement_id,
            **serializer.validated_data,
        )
        logger.info("[EVIDENCE] confirmed item=%s status=%s", item.pk, item.upload_status)
        return ok({"evidence": EvidenceItemSerializer(item).data}, status_code=201)

    def get(self, request, agreement_id: int):
        self._get_visible_agreement(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        items = EvidenceSelector.list_confirmed_evidence(agreement_id=agreement_id)
        logger.info("[EVIDENCE] list_evidence agreement=%s count=%s", agreement_id, len(items))
        return ok({"evidence": EvidenceItemSerializer(items, many=True).data})
