from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.disputes.api.serializers import DisputeCreateSerializer, DisputeSerializer
from apps.disputes.models import Dispute
from apps.disputes.selectors import DisputeSelector
from apps.disputes.services import DisputeService
from apps.parties.models import Party
from common.exceptions import DomainError
from common.phone_numbers import phone_lookup_values
from common.responses import ok


class DisputeCollectionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int, account_phone: str):
        try:
            return AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=account_id,
                account_phone=account_phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

    def _caller_party(self, agreement, user):
        phone = getattr(user.account, "phone", "") or getattr(user, "phone", "")
        return Party.objects.filter(
            agreement=agreement,
            phone__in=phone_lookup_values(phone),
        ).first()

    def get(self, request, agreement_id: int):
        self._get_agreement(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        disputes = DisputeSelector.list_for_agreement(agreement_id=agreement_id)
        return ok({"disputes": DisputeSerializer(disputes, many=True).data})

    def post(self, request, agreement_id: int):
        try:
            agreement = self._get_agreement(
                agreement_id,
                request.user.account.pk,
                request.user.account.phone,
            )
        except Http404:
            return Response({"status": "error", "message": "Agreement not found"}, status=404)

        caller_party = self._caller_party(agreement, request.user)
        if caller_party is None:
            return Response(
                {
                    "status": "error",
                    "message": (
                        "Authenticated user is not a verified party on this agreement."
                    ),
                },
                status=403,
            )
        party_id = request.data.get("raised_by_party_id")
        if party_id and str(party_id) != str(caller_party.pk):
            return Response(
                {
                    "status": "error",
                    "message": "Disputes can only be opened for the authenticated party.",
                },
                status=403,
            )

        serializer = DisputeCreateSerializer(data={
            "raised_by_party_id": caller_party.pk,
            "reason": request.data.get("reason", ""),
        })
        if not serializer.is_valid():
            return Response({"status": "error", "message": serializer.errors}, status=400)

        try:
            dispute = DisputeService.open_dispute(
                agreement_id=agreement_id,
                raised_by_party_id=serializer.validated_data["raised_by_party_id"],
                reason=serializer.validated_data["reason"],
            )
        except DomainError as e:
            return Response({"status": "error", "message": str(e)}, status=400)

        return ok({"dispute": DisputeSerializer(dispute).data}, status_code=201)


class DisputeRootView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        disputes = DisputeSelector.list_for_account(
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        return ok({"disputes": DisputeSerializer(disputes, many=True).data})


class DisputeLookupView(APIView):
    """Look up a single dispute by ID without needing agreement_id."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_visible_dispute(self, request, dispute_id: int) -> Dispute:
        try:
            dispute = Dispute.objects.select_related("raised_by", "agreement").get(
                pk=dispute_id
            )
            AgreementSelector.get_agreement_detail(
                dispute.agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
            return dispute
        except (Dispute.DoesNotExist, Agreement.DoesNotExist):
            raise Http404 from None

    def get(self, request, dispute_id: int):
        dispute = self._get_visible_dispute(request, dispute_id)
        return ok({"dispute": DisputeSerializer(dispute).data})

    def post(self, request, dispute_id: int):
        dispute = self._get_visible_dispute(request, dispute_id)
        case_pack = DisputeService.generate_case_pack(dispute=dispute)
        return ok({"case_pack": case_pack})


class DisputeDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id: int, dispute_id: int):
        try:
            dispute = DisputeSelector.get(dispute_id=dispute_id, agreement_id=agreement_id)
        except Dispute.DoesNotExist:
            raise Http404 from None
        try:
            AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        return ok({"dispute": DisputeSerializer(dispute).data})

    def post(self, request, agreement_id: int, dispute_id: int):
        try:
            dispute = DisputeSelector.get(dispute_id=dispute_id, agreement_id=agreement_id)
        except Dispute.DoesNotExist:
            raise Http404 from None
        try:
            AgreementSelector.get_agreement_detail(
                agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except Agreement.DoesNotExist:
            raise Http404 from None
        case_pack = DisputeService.generate_case_pack(dispute=dispute)
        return ok({"case_pack": case_pack})
