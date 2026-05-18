import asyncio

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.push import send_to_user
from config.asgi import application


@pytest.fixture
def user_with_token(db, django_user_model):
    user = django_user_model.objects.create_user(phone="+233500000001")
    refresh = RefreshToken.for_user(user)
    return user, str(refresh.access_token)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_connect_with_valid_token(user_with_token):
    user, token = user_with_token
    communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_connect_with_invalid_token_rejected(db):
    communicator = WebsocketCommunicator(application, "/ws/notifications/?token=invalidtoken")
    connected, _ = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_receive_push_notification(user_with_token):
    user, token = user_with_token
    communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
    connected, _ = await communicator.connect()
    assert connected

    send_to_user(user.phone, "agreement.sealed", {"agreement_id": 1, "title": "Test"})

    await asyncio.sleep(0.5)

    response = await communicator.receive_json_from(timeout=2)
    assert response["type"] == "agreement.sealed"
    assert response["payload"]["agreement_id"] == 1
    assert response["timestamp"]

    await communicator.disconnect()
