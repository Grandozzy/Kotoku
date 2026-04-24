from django.http import Http404
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.parties.api.serializers import (
    PartiesPatchSerializer,
    PartiesSetSerializer,
    PartyOutputSerializer,
)
from apps.parties.selectors import PartySelector
from apps.parties.services import PartyService
from common.responses import ok


class PartiesView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        """Ownership-scoped agreement lookup; raises 404 if not found or not owned."""
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id, account_id=account_id
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def post(self, request, agreement_id: int):
        """Replace the full party set for a draft agreement."""
        self._get_agreement(agreement_id, account_id=request.user.account.pk)
        serializer = PartiesSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parties = PartyService.set_parties(
            agreement_id=agreement_id,
            initiator_account=request.user.account,
            parties_data=serializer.validated_data["parties"],
        )
        return ok({"parties": PartyOutputSerializer(parties, many=True).data})

    def patch(self, request, agreement_id: int):
        """Partially update existing parties matched by role."""
        self._get_agreement(agreement_id, account_id=request.user.account.pk)
        serializer = PartiesPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parties = PartyService.patch_parties(
            agreement_id=agreement_id,
            initiator_account=request.user.account,
            parties_data=serializer.validated_data["parties"],
        )
        return ok({"parties": PartyOutputSerializer(parties, many=True).data})

    def get(self, request, agreement_id: int):
        """List all parties for an agreement."""
        self._get_agreement(agreement_id, account_id=request.user.account.pk)
        parties = PartySelector.list_parties(agreement_id=agreement_id)
        return ok({"parties": PartyOutputSerializer(parties, many=True).data})
