import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class InfobipDlrWebhookView(View):
    """Receives Infobip delivery report (DLR) callbacks.

    Configure the callback URL in the Infobip dashboard:
      https://<your-api-domain>/api/webhooks/infobip/dlr/?secret=<INFOBIP_WEBHOOK_SECRET>
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        expected = getattr(settings, "INFOBIP_WEBHOOK_SECRET", "")
        if expected and request.GET.get("secret") != expected:
            return HttpResponseForbidden("Invalid webhook secret")

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Infobip DLR: non-JSON body received")
            return HttpResponse(status=400)

        for result in payload.get("results", []):
            status = result.get("status", {})
            logger.info(
                "Infobip DLR received",
                extra={
                    "dlr": {
                        "message_id": result.get("messageId"),
                        "bulk_id": result.get("bulkId"),
                        "to": result.get("to", "")[:4] + "***",
                        "channel": result.get("channel"),
                        "status_group": status.get("groupName"),
                        "status_name": status.get("name"),
                        "status_description": status.get("description"),
                        "done_at": result.get("doneAt"),
                    }
                },
            )

        return HttpResponse(status=200)
