import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import DeviceSession, User

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    @staticmethod
    def _get_authorization_header(scope) -> str:
        for key, value in scope.get("headers", []):
            if key == b"authorization":
                return value.decode("utf-8", errors="ignore")
        return ""

    async def connect(self):
        auth_header = self._get_authorization_header(self.scope)
        token_str = ""
        if auth_header.lower().startswith("bearer "):
            token_str = auth_header[7:].strip()

        if not token_str:
            await self.close(code=4001)
            return

        try:
            access_token = AccessToken(token_str)
            self.user = await User.objects.aget(pk=access_token["user_id"])
        except (InvalidToken, TokenError, User.DoesNotExist):
            await self.close(code=4001)
            return

        # G5: Check that the device session is not revoked on connect.
        # We accept the 24-hour access token window for already-connected clients.
        session_id = access_token.get("device_session_id")
        if session_id:
            try:
                session = await DeviceSession.objects.aget(id=session_id)
                if session.is_revoked:
                    logger.info(
                        "WS rejected: session %s revoked for user=%s", session_id, self.user
                    )
                    await self.close(code=4003)
                    return
            except DeviceSession.DoesNotExist:
                await self.close(code=4003)
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
