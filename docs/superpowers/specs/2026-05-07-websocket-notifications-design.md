# WebSocket Real-Time Notification System

## Problem

Agreement state changes (reopen requests, OTP confirmations, sealing) are invisible to the other party until they manually reload. Two specific bottlenecks:

1. Account A requests reopen → Account B sees nothing until reload
2. Account B confirms OTP → Account A sees nothing until reload

Current approach relies on TanStack Query cache invalidation (only works on the mutating device) and a 5s poll on vault detail (only for PDF status).

## Solution

Django Channels WebSocket connection per authenticated user. Backend pushes typed events to user-specific channel groups via Redis. Frontend receives events and invalidates relevant query caches.

## Architecture

### Backend

**Dependencies:** `channels[daphne]>=4.0`, `channels-redis>=4.2`

**Channel layer:** Redis DB 2 (`channels_redis`) — separate from Celery (DB 0/1) and Django cache (DB 0).

**ASGI stack:**
```
ProtocolTypeRouter
  "http" → Django ASGI
  "websocket" → AuthMiddlewareStack → NotificationConsumer
```

**Consumer: `NotificationConsumer`**

- Endpoint: `ws://host/ws/notifications/?token=<drf_token>`
- On connect: validate token, get user's phone, join group `user.<phone>`
- On disconnect: leave group
- On receive: no-op (server-push only for now)
- Class method `send_to_user(phone, event_type, payload)` broadcasts to group

**Auth:** Query param `token` validated against `rest_framework.authtoken.models.Token`. Connection rejected (code 4001) if invalid.

**Event format:**
```json
{
  "type": "<event_type>",
  "payload": { ... },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Event types (starting set):**

| Event | Trigger | Payload |
|---|---|---|
| `agreement.reopen_requested` | Party A calls request-reopen | `{agreement_id, title}` |
| `agreement.reopen_confirmed` | Both parties confirmed → active | `{agreement_id, title}` |
| `agreement.sealed` | Agreement sealed | `{agreement_id, title}` |
| `agreement.updated` | Agreement edited and re-sealed | `{agreement_id, title}` |

**Where events are sent:** In the existing service/view code, after the state transition succeeds. Call `send_to_user(phone, type, payload)` for each party.

**ASGI config changes:** Replace `config/asgi.py` with Channels `ProtocolTypeRouter`. Add `CHANNEL_LAYERS` to settings.

**Deployment:** Swap `gunicorn` for `daphne` in docker-compose web service.

### Frontend

**No new dependencies.** React Native has built-in WebSocket.

**Hook: `useNotifications()`**

- Connects to `ws://<API_HOST>/ws/notifications/?token=<auth_token>`
- Reads API host from existing api client config
- Reads auth token from session store
- On message: parses event, calls `queryClient.invalidateQueries()` for relevant keys
- Auto-reconnects with exponential backoff (1s → 2s → 4s → 8s → max 30s)
- Pauses connection when `AppState === 'background'`, resumes on `'active'`
- Returns `{ connected: boolean, lastEvent: Event | null }`

**Event → cache invalidation mapping:**

| Event | Invalidated queries |
|---|---|
| `agreement.reopen_requested` | `["vault"]`, `["vault", agreement_id]`, `["pending-actions"]` |
| `agreement.reopen_confirmed` | `["vault"]`, `["vault", agreement_id]`, `["pending-actions"]` |
| `agreement.sealed` | `["vault"]`, `["vault", agreement_id]`, `["pending-actions"]` |
| `agreement.updated` | `["vault"]`, `["vault", agreement_id]`, `["pending-actions"]` |

**Mount point:** `(main)/_layout.tsx` — one connection for the whole authenticated session.

### What Gets Removed

- `refetchInterval` on `useVaultRecord` for sealed/reopen_requested statuses (polling replaced by push)
- `refetchInterval` on `usePendingActions` (polling replaced by push)
- Keep the `refetchInterval` for `pdfStatus === "pending"` (PDF generation is async, push not wired to S3 callbacks)

### Security

- Token-based auth on WebSocket connect — same DRF tokens used for REST API
- Consumer rejects connection if token invalid or missing
- Channel groups scoped to `user.<phone>` — no cross-user leakage
- No user-to-user messaging — server-push only

## Files to Create/Modify

### Backend (new)
- `apps/notifications/consumers.py` — NotificationConsumer
- `apps/notifications/routing.py` — WebSocket URL routing
- `apps/notifications/tests/test_consumer.py` — Consumer tests

### Backend (modify)
- `config/asgi.py` — ProtocolTypeRouter with Channels
- `config/settings/base.py` — CHANNEL_LAYERS config, add `channels` to INSTALLED_APPS
- `pyproject.toml` — add `channels[daphne]>=4.0`, `channels-redis>=4.2`
- `docker-compose.yml` — web command: `daphne` instead of gunicorn
- `scripts/run_dev.sh` — use `daphne` for dev server
- `apps/agreements/services.py` or relevant view — add `send_to_user()` calls after state transitions
- `apps/consent/views.py` — push event on seal
- `apps/vault/views.py` — push events on reopen request/confirm

### Frontend (new)
- `src/hooks/useNotifications.ts` — WebSocket hook

### Frontend (modify)
- `app/(main)/_layout.tsx` — mount `useNotifications()`
- `src/features/vault/useVault.ts` — remove polling for sealed/reopen_requested
- `src/features/agreements/usePendingActions.ts` — remove polling
