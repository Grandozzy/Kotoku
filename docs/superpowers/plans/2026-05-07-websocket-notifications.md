# WebSocket Real-Time Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time WebSocket notifications so agreement state changes (reopen requests, OTP confirmations, sealing) are instantly visible to all parties without manual reload.

**Architecture:** Django Channels over Redis channel layer. Each user joins a group `user.<phone>` on connect. Backend pushes typed JSON events to user groups after state transitions. Frontend `useNotifications` hook receives events and invalidates TanStack Query caches.

**Tech Stack:** `channels[daphne]>=4.0`, `channels-redis>=4.2`, React Native built-in WebSocket, Redis (already running)

---

## Task 1: Install backend dependencies and configure channel layers

**Files:**
- Modify: `kotoku-backend/pyproject.toml`
- Modify: `kotoku-backend/config/settings/base.py`

- [ ] **Step 1: Add channels dependencies to pyproject.toml**

In `kotoku-backend/pyproject.toml`, add to the `dependencies` array (after the `sentry-sdk` line):

```toml
  "channels[daphne]>=4.0,<5.0",
  "channels-redis>=4.2,<5.0",
```

- [ ] **Step 2: Add channels to INSTALLED_APPS**

In `kotoku-backend/config/settings/base.py`, add `"channels",` to `INSTALLED_APPS` (after `"rest_framework.authtoken",`):

```python
    "channels",
```

- [ ] **Step 3: Add CHANNEL_LAYERS config**

In `kotoku-backend/config/settings/base.py`, add after the `CACHES` dict (after line 119):

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0").replace("/0", "/2")],
        },
    },
}
```

This uses Redis DB 2 to avoid clashing with Celery (DB 0/1) and Django cache (DB 0).

- [ ] **Step 4: Install deps**

Run: `cd D:\Oscar\kotoku-backend\kotoku-backend && pip install "channels[daphne]>=4.0,<5.0" "channels-redis>=4.2,<5.0"`

- [ ] **Step 5: Verify import works**

Run: `python -c "import channels; print(channels.__version__)"`

Expected: version string like `4.x.x`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml config/settings/base.py
git commit -m "feat: add channels dependency and channel layer config"
```

---

## Task 2: Create the WebSocket consumer

**Files:**
- Create: `kotoku-backend/apps/notifications/consumers.py`
- Create: `kotoku-backend/apps/notifications/routing.py`

- [ ] **Step 1: Write the consumer**

Create `kotoku-backend/apps/notifications/consumers.py`:

```python
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
```

- [ ] **Step 2: Write the routing file**

Create `kotoku-backend/apps/notifications/routing.py`:

```python
from django.urls import re_path

from .consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]
```

- [ ] **Step 3: Commit**

```bash
git add apps/notifications/consumers.py apps/notifications/routing.py
git commit -m "feat: add WebSocket notification consumer and routing"
```

---

## Task 3: Wire ASGI and create the push helper

**Files:**
- Modify: `kotoku-backend/config/asgi.py`
- Create: `kotoku-backend/apps/notifications/push.py`

- [ ] **Step 1: Update ASGI config**

Replace the entire content of `kotoku-backend/config/asgi.py` with:

```python
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

django_asgi_app = get_asgi_application()

from apps.notifications.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns),
        ),
    }
)
```

- [ ] **Step 2: Create the push helper**

Create `kotoku-backend/apps/notifications/push.py`:

```python
import json
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
        loop = asyncio.get_running_loop()
        loop.create_task(_async_send_to_user(phone, event_type, payload))
    except RuntimeError:
        asyncio.run(_async_send_to_user(phone, event_type, payload))
```

- [ ] **Step 3: Commit**

```bash
git add config/asgi.py apps/notifications/push.py
git commit -m "feat: wire ASGI for WebSocket and add send_to_user helper"
```

---

## Task 4: Switch dev server to daphne

**Files:**
- Modify: `kotoku-backend/scripts/run_dev.sh`
- Modify: `kotoku-backend/docker-compose.yml`

- [ ] **Step 1: Update run_dev.sh**

Replace `kotoku-backend/scripts/run_dev.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

./scripts/wait_for_db.sh
python manage.py migrate --noinput
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

- [ ] **Step 2: Update docker-compose web command**

In `kotoku-backend/docker-compose.yml`, change the `web` service `command` from:

```yaml
    command: ./scripts/run_dev.sh
```

to (keep as is — it already calls run_dev.sh which now uses daphne). No change needed if using the script.

- [ ] **Step 3: Verify daphne starts**

Run: `cd D:\Oscar\kotoku-backend\kotoku-backend && daphne -b 127.0.0.1 -p 8000 config.asgi:application`

Expected: `Starting server at 127.0.0.1:8000` (Ctrl+C to stop)

- [ ] **Step 4: Commit**

```bash
git add scripts/run_dev.sh docker-compose.yml
git commit -m "feat: switch dev server to daphne for WebSocket support"
```

---

## Task 5: Hook push notifications into agreement state transitions

**Files:**
- Modify: `kotoku-backend/apps/agreements/services.py`
- Modify: `kotoku-backend/apps/consent/services.py`

- [ ] **Step 1: Push event on reopen request**

In `kotoku-backend/apps/agreements/services.py`, add import at top:

```python
from apps.notifications.push import send_to_user
```

In `request_reopen()` method, after `agreement.save(update_fields=["status", "updated_at"])` (around line 250) and before the audit event, add:

```python
        from apps.parties.models import Party

        parties = Party.objects.filter(agreement=agreement)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, "agreement.reopen_requested", {
                    "agreement_id": agreement.pk,
                    "title": agreement.title,
                })
```

- [ ] **Step 2: Push event on bilateral reopen complete**

In the same file, in `complete_bilateral_reopen()` method, after `agreement.save(update_fields=...)` (around line 281) and before the audit event, add:

```python
        from apps.parties.models import Party

        parties = Party.objects.filter(agreement=agreement)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, "agreement.reopen_confirmed", {
                    "agreement_id": agreement.pk,
                    "title": agreement.title,
                })
```

- [ ] **Step 3: Push event on seal**

In the same file, in `seal_agreement()` method, after `agreement.save(update_fields=...)` (around line 213) and before the audit event, add:

```python
        from apps.parties.models import Party

        parties = Party.objects.filter(agreement=agreement)
        for p in parties:
            if p.phone:
                send_to_user(p.phone, "agreement.sealed", {
                    "agreement_id": agreement.pk,
                    "title": agreement.title,
                })
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `cd D:\Oscar\kotoku-backend\kotoku-backend && python -m pytest tests/ apps/ -x -q --tb=short`

Expected: All existing tests pass (the `send_to_user` calls will silently fail if no channel layer is configured in test settings, which is fine — the `RuntimeError` catch in the sync wrapper handles this).

- [ ] **Step 5: Commit**

```bash
git add apps/agreements/services.py
git commit -m "feat: push WebSocket events on agreement state transitions"
```

---

## Task 6: Write consumer tests

**Files:**
- Create: `kotoku-backend/apps/notifications/tests/test_consumer.py`

- [ ] **Step 1: Write the test**

Create `kotoku-backend/apps/notifications/tests/test_consumer.py`:

```python
import json

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework.authtoken.models import Token

from apps.notifications.consumers import NotificationConsumer
from apps.notifications.push import send_to_user
from config.asgi import application


@pytest.fixture
def user_with_token(db, django_user_model):
    user = django_user_model.objects.create_user(
        username="+233500000001",
        phone="+233500000001",
        password="testpass123",
    )
    token = Token.objects.create(user=user)
    return user, token


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_connect_with_valid_token(user_with_token):
    user, token = user_with_token
    communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token.key}")
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
    communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token.key}")
    connected, _ = await communicator.connect()
    assert connected

    send_to_user(user.phone, "agreement.sealed", {"agreement_id": 1, "title": "Test"})

    import asyncio
    await asyncio.sleep(0.5)

    response = await communicator.receive_json_from(timeout=2)
    assert response["type"] == "agreement.sealed"
    assert response["payload"]["agreement_id"] == 1
    assert response["timestamp"]

    await communicator.disconnect()
```

Note: This test requires `pytest-asyncio`. Add `"pytest-asyncio>=0.24,<1.0"` to `pyproject.toml` optional dev deps if not present.

- [ ] **Step 2: Run tests**

Run: `cd D:\Oscar\kotoku-backend\kotoku-backend && python -m pytest apps/notifications/tests/test_consumer.py -v`

Expected: All 3 tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/notifications/tests/test_consumer.py
git commit -m "test: add WebSocket consumer tests"
```

---

## Task 7: Create frontend useNotifications hook

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/hooks/useNotifications.ts`

- [ ] **Step 1: Write the hook**

Create `Kotoku-frontend/kotoku-mobile/src/hooks/useNotifications.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, type AppStateStatus } from "react-native";

import { API_BASE_URL } from "@/constants/config";
import { getToken } from "@/lib/secureStore";
import { queryClient } from "@/lib/queryClient";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;
const WS_PATH = "/ws/notifications/";

interface WsEvent {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

function getWsUrl(token: string): string {
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}${WS_PATH}?token=${token}`;
}

const INVALIDATION_MAP: Record<string, string[]> = {
  "agreement.reopen_requested": ["vault", "pending-actions"],
  "agreement.reopen_confirmed": ["vault", "pending-actions"],
  "agreement.sealed": ["vault", "pending-actions"],
  "agreement.updated": ["vault", "pending-actions"],
};

function handleEvent(event: WsEvent) {
  const prefixes = INVALIDATION_MAP[event.type];
  if (!prefixes) return;

  for (const prefix of prefixes) {
    queryClient.invalidateQueries({ queryKey: [prefix] });
  }

  const agreementId = event.payload.agreement_id;
  if (typeof agreementId === "number") {
    queryClient.invalidateQueries({ queryKey: ["vault", agreementId] });
  }
}

export function useNotifications() {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(RECONNECT_BASE_MS);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);

  const connect = useCallback(async () => {
    const token = await getToken();
    if (!token || cancelledRef.current) return;

    const ws = new WebSocket(getWsUrl(token));
    wsRef.current = ws;

    ws.onopen = () => {
      if (cancelledRef.current) return;
      setConnected(true);
      reconnectDelay.current = RECONNECT_BASE_MS;
    };

    ws.onmessage = (e) => {
      if (cancelledRef.current) return;
      try {
        const event: WsEvent = JSON.parse(e.data);
        handleEvent(event);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (cancelledRef.current) return;
      setConnected(false);
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (cancelledRef.current) return;
    reconnectTimer.current = setTimeout(() => {
      reconnectDelay.current = Math.min(
        reconnectDelay.current * 2,
        RECONNECT_MAX_MS,
      );
      connect();
    }, reconnectDelay.current);
  }, [connect]);

  useEffect(() => {
    cancelledRef.current = false;
    connect();

    return () => {
      cancelledRef.current = true;
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  useEffect(() => {
    const handleAppState = (nextState: AppStateStatus) => {
      if (nextState === "active") {
        if (
          !wsRef.current ||
          wsRef.current.readyState === WebSocket.CLOSED
        ) {
          reconnectDelay.current = RECONNECT_BASE_MS;
          connect();
        }
      } else if (nextState === "background") {
        wsRef.current?.close();
      }
    };

    const sub = AppState.addEventListener("change", handleAppState);
    return () => sub.remove();
  }, [connect]);

  return { connected };
}
```

- [ ] **Step 2: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/src/hooks/useNotifications.ts
git commit -m "feat: add useNotifications WebSocket hook"
```

---

## Task 8: Mount useNotifications and remove polling

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/app/_layout.tsx`
- Modify: `Kotoku-frontend/kotoku-mobile/src/features/vault/useVault.ts`
- Modify: `Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts`

- [ ] **Step 1: Mount the hook in root layout**

In `Kotoku-frontend/kotoku-mobile/app/_layout.tsx`, add import:

```typescript
import { useNotifications } from "@/hooks/useNotifications";
```

Inside the `AuthGuard` component (around line 34), add:

```typescript
  useNotifications();
```

This runs the WebSocket connection only when the user is authenticated (AuthGuard only renders children when authenticated).

- [ ] **Step 2: Remove reopen polling from useVaultRecord**

In `Kotoku-frontend/kotoku-mobile/src/features/vault/useVault.ts`, replace the `refetchInterval` function with:

```typescript
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      if (data.pdfStatus === "pending") return 5000;
      return false;
    },
```

This removes the `sealed` / `reopen_requested` polling — WebSocket push handles those now.

- [ ] **Step 3: Remove polling from usePendingActions**

In `Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts`, remove the `refetchInterval: 15000` line. The query should go back to:

```typescript
export function usePendingActions() {
  return useQuery({
    queryKey: ["pending-actions"],
    queryFn: fetchPendingActions,
  });
}
```

- [ ] **Step 4: Run TSC**

Run: `cd D:\Oscar\kotoku-backend\Kotoku-frontend\kotoku-mobile && npx tsc --noEmit --pretty 2>&1 | Select-Object -First 10`

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/app/_layout.tsx Kotoku-frontend/kotoku-mobile/src/features/vault/useVault.ts Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts
git commit -m "feat: mount useNotifications and remove polling"
```

---

## Task 9: End-to-end verification

**Files:** None — manual verification

- [ ] **Step 1: Start backend with daphne**

Run: `cd D:\Oscar\kotoku-backend\kotoku-backend && daphne -b 0.0.0.0 -p 8000 config.asgi:application`

- [ ] **Step 2: Start frontend**

Run: `cd D:\Oscar\kotoku-backend\Kotoku-frontend\kotoku-mobile && npx expo start`

- [ ] **Step 3: Test reopen flow on two devices**

1. Device A: Create and seal an agreement between A and B
2. Device A: Open vault detail → tap "Request Reopen"
3. Device B: Should see the agreement status change to "Reopen Requested" within ~1 second without reload
4. Device B: Enter OTP and confirm
5. Device A: Should see the status change to "Active" within ~1 second without reload

- [ ] **Step 4: Verify seal notification**

1. Device A: Edit the agreement and submit
2. Both devices go through the consent flow
3. On seal, both devices should see the vault update instantly
