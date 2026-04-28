import { useEffect, useRef } from "react";

import {
  getPendingItems,
  markComplete,
  markFailed,
  markInFlight,
} from "@/db/syncQueue";
import { useNetworkStatus } from "./useNetworkStatus";

const MAX_RETRIES = 3;

/**
 * Drains the SQLite sync queue when connectivity is restored.
 * Each pending item is dispatched via its registered handler.
 *
 * Handlers are registered by action type so each feature owns its retry logic.
 * Currently a no-op shell — wire handlers as features are completed.
 */
type SyncHandler = (payload: Record<string, unknown>) => Promise<void>;

const handlers: Record<string, SyncHandler> = {};

export function registerSyncHandler(
  actionType: string,
  handler: SyncHandler,
): void {
  handlers[actionType] = handler;
}

export function useSyncQueue(): void {
  const { isConnected, isInternetReachable } = useNetworkStatus();
  const isOnline = isConnected && isInternetReachable;
  const drainingRef = useRef(false);

  useEffect(() => {
    if (!isOnline || drainingRef.current) return;

    async function drain() {
      drainingRef.current = true;
      try {
        const items = await getPendingItems();
        for (const item of items) {
          const handler = handlers[item.action_type];
          if (!handler) continue;

          if (item.retry_count >= MAX_RETRIES) {
            await markFailed(item.id, true); // permanent failure
            continue;
          }

          await markInFlight(item.id);
          try {
            await handler(item.payload);
            await markComplete(item.id);
          } catch {
            // 409/404 → permanent; anything else → retry
            await markFailed(item.id, false);
          }
        }
      } finally {
        drainingRef.current = false;
      }
    }

    drain();
  }, [isOnline]);
}
