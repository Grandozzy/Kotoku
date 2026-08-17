from django.http import Http404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.agreements.models import Agreement
from apps.agreements.selectors import AgreementSelector
from apps.parties.api.serializers import (
    PartiesPatchSerializer,
    PartiesSetSerializer,
    PartyOutputSerializer,
)
from apps.parties.invite_service import PartyInviteService
from apps.parties.models import Party
from apps.parties.selectors import PartySelector
from apps.parties.services import PartyService
from common.exceptions import DomainError
from common.responses import ok


class PartiesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_agreement(self, agreement_id: int, account_id: int):
        """Ownership-scoped agreement lookup; raises 404 if not found or not owned."""
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
        """Replace the full party set for a draft agreement."""
        self._get_agreement(agreement_id, account_id=request.user.account.pk)
        serializer = PartiesSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parties = PartyService.set_parties(
            agreement_id=agreement_id,
            initiator_account=request.user.account,
            parties_data=serializer.validated_data["parties"],
        )
        serializer_context = PartyOutputSerializer.context_for_parties(parties)
        return ok({"parties": PartyOutputSerializer(parties, many=True, context=serializer_context).data})

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
        serializer_context = PartyOutputSerializer.context_for_parties(parties)
        return ok({"parties": PartyOutputSerializer(parties, many=True, context=serializer_context).data})

    def get(self, request, agreement_id: int):
        """List all parties for an agreement."""
        self._get_visible_agreement(
            agreement_id,
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        parties = PartySelector.list_parties(agreement_id=agreement_id)
        serializer_context = PartyOutputSerializer.context_for_parties(parties)
        return ok({"parties": PartyOutputSerializer(parties, many=True, context=serializer_context).data})


class PartyInviteSendView(APIView):
    """POST /api/agreements/{agreement_id}/parties/invite/{role}/

    Owner-only. Creates (or replaces) an identity invite for the named party role
    and sends the deep-link token to that party's phone via SMS.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, agreement_id: int, role: str):
        try:
            AgreementSelector.get_owned_agreement_detail(
                agreement_id, account_id=request.user.account.pk
            )
        except Agreement.DoesNotExist:
            raise Http404 from None

        try:
            party = Party.objects.get(agreement_id=agreement_id, role=role)
        except Party.DoesNotExist:
            raise Http404 from None

        try:
            invite = PartyInviteService.create_and_send(party=party)
        except DomainError as exc:
            return Response({"status": "error", "message": str(exc)}, status=400)

        return ok(
            {
                "invite": {
                    "role": party.role,
                    "party_name": party.display_name,
                    "expires_at": invite.expires_at.isoformat(),
                }
            },
            status_code=201,
        )


class InviteDetailView(APIView):
    """GET /api/invites/{token}/

    No authentication required. Returns invite metadata so the mobile app can
    show a preview before the user authenticates and claims.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token: str):
        try:
            detail = PartyInviteService.get_detail(token=token)
        except DomainError as exc:
            status = 404 if exc.code is None else 410
            return Response({"status": "error", "message": str(exc), "code": exc.code}, status=status)
        return ok({"invite": detail})


class InviteClaimView(APIView):
    """POST /api/invites/{token}/claim/

    Requires authentication. The authenticated account's phone must match the invited
    party's phone — fails closed with 403 if it does not (Section 5 of impl rules).
    Returns {agreement_id, role} so the app can navigate to the identity screen.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, token: str):
        try:
            result = PartyInviteService.claim(token=token, account=request.user.account)
        except DomainError as exc:
            if exc.code == "phone_mismatch":
                return Response(
                    {"status": "error", "message": str(exc), "code": exc.code}, status=403
                )
            return Response(
                {"status": "error", "message": str(exc), "code": exc.code}, status=410
            )
        return ok(result)
