"use client";

import { useEffect } from "react";
import { refreshAccessToken } from "@/lib/apiClient";
import { useSessionStore } from "@/store/sessionStore";

export function AuthBootstrap() {
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const accessToken = useSessionStore((s) => s.accessToken);
  const setBootstrapping = useSessionStore((s) => s.setBootstrapping);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== null && event.key !== "kotoku-session") return;
      void useSessionStore.persist.rehydrate();
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated || accessToken) {
      setBootstrapping(false);
      return;
    }

    let cancelled = false;
    setBootstrapping(true);

    void refreshAccessToken().finally(() => {
      if (!cancelled) setBootstrapping(false);
    });

    return () => {
      cancelled = true;
    };
  }, [accessToken, hasHydrated, isAuthenticated, setBootstrapping]);

  return null;
}
