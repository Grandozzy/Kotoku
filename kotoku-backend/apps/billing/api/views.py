from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.selectors import get_current_plan_usage
from common.exceptions import DomainError
from common.responses import ok


class CurrentPlanView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            account = request.user.account
        except Exception:
            raise DomainError("Account not found for this user.")
        data = get_current_plan_usage(account)
        return ok(data)
