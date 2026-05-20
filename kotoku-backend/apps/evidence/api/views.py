import logging

from django.http import Http404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.evidence.api.serializers import (
    ConfirmUploadSerializer,
    EvidenceItemSerializer,
    UploadUrlRequestSerializer,
)
from apps.evidence.models import EvidenceItem
from apps.evidence.selectors import EvidenceSelector
from apps.evidence.services import EvidenceService
from common.responses import ok

logger = logging.getLogger("kotoku")


class EvidenceUploadUrlView(APIView):
    """POST /api/agreements/{id}/evidence/upload-url

    Issue a presigned PUT URL so the client can upload directly to object storage.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_owned_agreement_detail(
                agreement_id, account_id=account_id
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def post(self, request, agreement_id: int):
        self._get_agreement(agreement_id, account_id=request.user.account.pk)
        serializer = UploadUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info(
            "[EVIDENCE] generate_upload_url agreement=%s evidence_type=%s account=%s",
            agreement_id,
            serializer.validated_data["evidence_type"],
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

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_owned_agreement_detail(
                agreement_id, account_id=account_id
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

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
        self._get_agreement(agreement_id, account_id=request.user.account.pk)
        serializer = ConfirmUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info(
            "[EVIDENCE] confirm_upload agreement=%s evidence_type=%s",
            agreement_id,
            serializer.validated_data["evidence_type"],
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
