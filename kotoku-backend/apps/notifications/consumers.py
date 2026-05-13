import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Expect: ws://...?token=<access_jwt>
        qs = self.scope.get("query_string", b"").decode()
        token_str = ""
        for part in qs.split("&"):
            if part.startswith("token="):
                token_str = part[6:]
                break

        if not token_str:
            await self.close(code=4001)
            return

        try:
            access_token = AccessToken(token_str)
            self.user = await User.objects.aget(pk=access_token["user_id"])
        except (InvalidToken, TokenError, User.DoesNotExist):
            await self.close(code=4001)
            return

        phone = getattr(self.user, "phone", None) or self.user.username
        self.group_name = f"user.{phone.replace('+', '')}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WS connected: user=%s group=%s", self.user, self.group_name)

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info("WS disconnected: user=%s", getattr(self, "user", "?"))

    async def receive(self, text_data=None):
        pass

    async def notify(self, event):
        await self.send(text_data=json.dumps({
            "type": event["event_type"],
            "payload": event.get("payload", {}),
            "timestamp": event.get("timestamp"),
        }))
