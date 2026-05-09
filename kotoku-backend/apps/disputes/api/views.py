from django.http import Http404
import logging
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from apps.agreements.selectors import AgreementSelector
from apps.agreements.models import Agreement
from apps.parties.models import Party
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
        print(f"[DISPUTE] POST agreement_id={agreement_id}")
        print(f"[DISPUTE] data={request.data}")
        try:
            agreement = self._get_agreement(agreement_id, request.user.account.pk)
        except Http404:
            print("[DISPUTE] Agreement not found")
            return Response({"status": "error", "message": "Agreement not found"}, status=404)
        
        # Auto-detect party from logged-in user if not provided
        party_id = request.data.get("raised_by_party_id")
        if not party_id:
            parties = Party.objects.filter(agreement_id=agreement_id)
            user_phone = getattr(request.user, 'username', None)
            print(f"[DISPUTE] Looking for party with phone={user_phone}")
            print(f"[DISPUTE] Available parties: {list(parties.values_list('id', 'phone'))}")
            for party in parties:
                if party.phone == user_phone:
                    party_id = party.id
                    print(f"[DISPUTE] Found matching party: {party_id}")
                    break
            if not party_id:
                party_id = parties.first().id if parties else None
                print(f"[DISPUTE] Using fallback party: {party_id}")
        
        # Create serializer data with detected party
        serializer_data = {
            "raised_by_party_id": party_id,
            "reason": request.data.get("reason", ""),
        }
        
        serializer = DisputeCreateSerializer(data=serializer_data)
        if not serializer.is_valid():
            print(f"[DISPUTE] Invalid: {serializer.errors}")
            return Response({"status": "error", "message": serializer.errors}, status=400)
        
        try:
            dispute = DisputeService.open_dispute(
                agreement_id=agreement_id,
                raised_by_party_id=serializer.validated_data["raised_by_party_id"],
                reason=serializer.validated_data["reason"],
            )
            print(f"[DISPUTE] Created dispute ID={dispute.id}")
        except Exception as e:
            print(f"[DISPUTE] Error: {e}")
            return Response({"status": "error", "message": str(e)}, status=400)
        
        return Response({"status": "ok", "data": DisputeSerializer(dispute).data}, status=201)


class DisputeRootView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        disputes = DisputeSelector.list_for_account(account_id=request.user.account.pk)
        return ok({"disputes": DisputeSerializer(disputes, many=True).data})


class DisputeLookupView(APIView):
    """Look up a single dispute by ID without needing agreement_id."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, dispute_id: int):
        try:
            dispute = Dispute.objects.select_related("raised_by", "agreement").get(
                pk=dispute_id, agreement__created_by=request.user.account
            )
        except Dispute.DoesNotExist:
            raise Http404 from None
        return ok({"dispute": DisputeSerializer(dispute).data})

    def post(self, request, dispute_id: int):
        try:
            dispute = Dispute.objects.select_related("raised_by", "agreement").get(
                pk=dispute_id, agreement__created_by=request.user.account
            )
        except Dispute.DoesNotExist:
            raise Http404 from None
        case_pack = DisputeService.generate_case_pack(dispute=dispute)
        return ok({"case_pack": case_pack})


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