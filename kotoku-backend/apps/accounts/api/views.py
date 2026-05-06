from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.api.serializers import AccountSerializer
from apps.accounts.selectors import AccountSelector
from common.exceptions import DomainError
from common.responses import ok


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
        })


class AccountListView(APIView):
    def get(self, request):  # type: ignore[override]
        serializer = AccountSerializer(AccountSelector.list_accounts(), many=True)
        return ok({"results": serializer.data})
