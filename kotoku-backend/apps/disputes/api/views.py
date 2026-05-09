from django.http import Http404
import logging
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from apps.agreements.selectors import AgreementSelector
from apps.agreements.models import Agreement
from apps.disputes.api.serializers import DisputeCreateSerializer, DisputeSerializer
from apps.disputes.models import Dispute
from apps.disputes.selectors import DisputeSelector
from apps.disputes.services import DisputeService
from common.exceptions import DomainError
from common.responses import ok


class DisputeCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_agreement_detail(agreement_id, account_id=account_id)
        except Agreement.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        disputes = DisputeSelector.list_for_agreement(agreement_id=agreement_id)
        return ok({"disputes": DisputeSerializer(disputes, many=True).data})

    from django.http import Http404
import logging
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.agreements.selectors import AgreementSelector
from apps.agreements.models import Agreement
from apps.disputes.api.serializers import DisputeCreateSerializer, DisputeSerializer
from apps.disputes.models import Dispute
from apps.disputes.selectors import DisputeSelector
from apps.disputes.services import DisputeService
from common.exceptions import DomainError
from common.responses import ok

logger = logging.getLogger(__name__)


class DisputeCollectionView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        try:
            return AgreementSelector.get_agreement_detail(agreement_id, account_id=account_id)
        except Agreement.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        disputes = DisputeSelector.list_for_agreement(agreement_id=agreement_id)
        return ok({"disputes": DisputeSerializer(disputes, many=True).data})

    def post(self, request, agreement_id: int):
        logger.info(f"POST /agreements/{agreement_id}/disputes/ request.data={request.data}")
        
        try:
            agreement = self._get_agreement(agreement_id, request.user.account.pk)
            logger.info(f"Agreement status: {agreement.status}")
        except Http404:
            return Response({"status": "error", "message": "Agreement not found"}, status=404)
        
        serializer = DisputeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer invalid: {serializer.errors}")
            return Response({"status": "error", "message": serializer.errors}, status=400)
        
        try:
            dispute = DisputeService.open_dispute(
                agreement_id=agreement_id,
                raised_by_party_id=serializer.validated_data["raised_by_party_id"],
                reason=serializer.validated_data["reason"],
            )
        except DomainError as e:
            logger.error(f"DomainError: {e}")
            return Response({"status": "error", "message": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Service error: {e}")
            return Response({"status": "error", "message": str(e)}, status=500)
        
        return Response({"status": "ok", "data": DisputeSerializer(dispute).data}, status=201)


class DisputeDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int, dispute_id: int):
        try:
            dispute = DisputeSelector.get(dispute_id=dispute_id, agreement_id=agreement_id)
        except Dispute.DoesNotExist:
            raise Http404 from None
        if dispute.agreement.created_by != request.user.account:
            raise Http404 from None
        return ok({"dispute": DisputeSerializer(dispute).data})

    def post(self, request, agreement_id: int, dispute_id: int):
        try:
            dispute = DisputeSelector.get(dispute_id=dispute_id, agreement_id=agreement_id)
        except Dispute.DoesNotExist:
            raise Http404 from None
        if dispute.agreement.created_by != request.user.account:
            raise Http404 from None
        case_pack = DisputeService.generate_case_pack(dispute=dispute)
        return ok({"case_pack": case_pack})
