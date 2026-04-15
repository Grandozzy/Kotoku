from rest_framework.views import APIView

from apps.accounts.api.serializers import AccountSerializer
from apps.accounts.selectors import AccountSelector
from common.responses import ok


class AccountListView(APIView):
    def get(self, request):  # type: ignore[override]
        serializer = AccountSerializer(AccountSelector.list_accounts(), many=True)
        return ok({"results": serializer.data})
