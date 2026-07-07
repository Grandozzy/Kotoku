import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, type AppStateStatus } from "react-native";

import { API_BASE_URL } from "@/constants/config";
import { queryClient } from "@/lib/queryClient";
import { useSessionStore } from "@/store/sessionStore";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;
const WS_PATH = "/ws/notifications/";

interface WsEvent {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

type ReactNativeWebSocketCtor = new (
  url: string,
  protocols?: string | string[],
  options?: { headers?: Record<string, string> },
) => WebSocket;

function getWsUrl(): string {
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}${WS_PATH}`;
}

const INVALIDATION_MAP: Record<string, string[]> = {
  "agreement.reopen_requested": ["vault", "pending-actions"],
  "agreement.reopen_confirmed": ["vault", "pending-actions"],
  "agreement.sealed": ["vault", "pending-actions"],
  "agreement.updated": ["vault", "pending-actions"],
  "vault.pdf_generating": ["vault"],
  "vault.pdf_ready": ["vault"],
  "vault.pdf_failed": ["vault"],
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
  const token = useSessionStore((s) => s.token);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(RECONNECT_BASE_MS);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);
  const appActiveRef = useRef(AppState.currentState === "active");

  const connect = useCallback(async () => {
    if (!token || !isAuthenticated || cancelledRef.current || !appActiveRef.current) {
      return;
    }
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    const ReactNativeWebSocket = WebSocket as unknown as ReactNativeWebSocketCtor;
    const ws = new ReactNativeWebSocket(getWsUrl(), undefined, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Client-Type": "mobile",
      },
    });
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
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [isAuthenticated, token]);

  const scheduleReconnect = useCallback(() => {
    if (
      cancelledRef.current ||
      !isAuthenticated ||
      !token ||
      !appActiveRef.current
    ) {
      return;
    }
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    reconnectTimer.current = setTimeout(() => {
      reconnectDelay.current = Math.min(
        reconnectDelay.current * 2,
        RECONNECT_MAX_MS,
      );
      connect();
    }, reconnectDelay.current);
  }, [connect, isAuthenticated, token]);

  useEffect(() => {
    cancelledRef.current = false;
    if (isAuthenticated && token) {
      connect();
    } else {
      wsRef.current?.close();
      wsRef.current = null;
      setConnected(false);
    }

    return () => {
      cancelledRef.current = true;
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect, isAuthenticated, token]);

  useEffect(() => {
    const handleAppState = (nextState: AppStateStatus) => {
      appActiveRef.current = nextState === "active";
      if (nextState === "active") {
        if (
          !wsRef.current ||
          wsRef.current.readyState === WebSocket.CLOSED
        ) {
          reconnectDelay.current = RECONNECT_BASE_MS;
          connect();
        }
      } else if (nextState === "background") {
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
        wsRef.current?.close();
        wsRef.current = null;
        setConnected(false);
      }
    };

    const sub = AppState.addEventListener("change", handleAppState);
    return () => sub.remove();
  }, [connect]);

  return { connected };
}
