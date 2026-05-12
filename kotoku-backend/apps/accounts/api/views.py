from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.api.serializers import AccountSerializer, UpdateProfileSerializer
from apps.accounts.selectors import AccountSelector
from apps.accounts.services import AccountService
from common.exceptions import DomainError
from common.responses import ok
from rest_framework.response import Response


class MeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            account = request.user.account
        except Exception:
            raise DomainError("Account not found for this user.")
        return ok({
            "id": account.pk,
            "phone": account.phone,
            "email": account.email,
            "full_name": account.full_name,
            "member_since": account.created_at.strftime("%B %Y"),
        })

    def patch(self, request):
        try:
            account = request.user.account
        except Exception:
            raise DomainError("Account not found for this user.")
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            account = AccountService.update_profile(
                account=account,
                full_name=serializer.validated_data.get("full_name"),
                email=serializer.validated_data.get("email") or None,
            )
        except DomainError as e:
            return Response({"status": "error", "message": str(e)}, status=400)
        return ok({
            "id": account.pk,
            "phone": account.phone,
            "email": account.email,
            "full_name": account.full_name,
            "member_since": account.created_at.strftime("%B %Y"),
        })


class AccountListView(APIView):
    def get(self, request):  # type: ignore[override]
        serializer = AccountSerializer(AccountSelector.list_accounts(), many=True)
        return ok({"results": serializer.data})
