import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token_key = self.scope.get("query_string", b"").decode()
        if token_key.startswith("token="):
            token_key = token_key[6:]
        if not token_key:
            await self.close(code=4001)
            return
        try:
            token = await Token.objects.select_related("user").aget(key=token_key)
        except Token.DoesNotExist:
            await self.close(code=4001)
            return
        self.user = token.user
        phone = getattr(self.user, "phone", None) or self.user.username
        self.group_name = f"user.{phone}"
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
