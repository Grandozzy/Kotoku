import logging
from datetime import datetime, timezone

from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


async def _async_send_to_user(phone: str, event_type: str, payload: dict):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("No channel layer configured — skipping push to %s", phone)
        return
    group_name = f"user.{phone}"
    await channel_layer.group_send(
        group_name,
        {
            "type": "notify",
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Pushed %s to %s", event_type, group_name)


def send_to_user(phone: str, event_type: str, payload: dict):
    """Synchronous wrapper — call from Django views/services."""
    import asyncio

    try:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_async_send_to_user(phone, event_type, payload))
        except RuntimeError:
            asyncio.run(_async_send_to_user(phone, event_type, payload))
    except Exception:
        logger.warning("Failed to push %s to %s", event_type, phone, exc_info=True)
