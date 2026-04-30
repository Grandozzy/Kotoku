from django.http import Http404
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

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

    def post(self, request, agreement_id: int):
        self._get_agreement(agreement_id, request.user.account.pk)
        serializer = DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute = DisputeService.open_dispute(
            agreement_id=agreement_id,
            raised_by_party_id=serializer.validated_data["raised_by_party_id"],
            reason=serializer.validated_data["reason"],
        )
        return ok({"dispute": DisputeSerializer(dispute).data}, status_code=201)
