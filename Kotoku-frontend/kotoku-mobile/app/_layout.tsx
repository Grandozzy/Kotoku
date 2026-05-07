import "@/lib/global.css";

import { QueryClientProvider } from "@tanstack/react-query";
import { Slot, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { runMigrations } from "@/db/migrations";
import { queryClient } from "@/lib/queryClient";
import { getAccountId, getPhone, getToken } from "@/lib/secureStore";
import { useSessionStore } from "@/store/sessionStore";
import { useNotifications } from "@/hooks/useNotifications";
import { useOfflineGuard } from "@/hooks/useOfflineGuard";
import { useSyncQueue } from "@/hooks/useSyncQueue";

function OfflineBanner() {
  const isOffline = useOfflineGuard();
  if (!isOffline) return null;
  return (
    <View className="bg-semantic-warning px-lg py-sm">
      <Text className="text-xs font-medium text-white text-center">
        You are offline. Changes will sync when you reconnect.
      </Text>
    </View>
  );
}

function SyncQueueRunner() {
  useSyncQueue();
  return null;
}

function AuthGuard() {
  const router = useRouter();
  const segments = useSegments();
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const setSession = useSessionStore((s) => s.setSession);

  useEffect(() => {
    (async () => {
      const [token, phone, accountId] = await Promise.all([
        getToken(),
        getPhone(),
        getAccountId(),
      ]);
      if (token && phone && accountId) {
        setSession(token, phone, accountId);
      }
    })();
  }, []);

  useEffect(() => {
    const inAuthGroup = segments[0] === "(auth)";
    if (!isAuthenticated && !inAuthGroup) {
      router.replace("/(auth)/welcome");
    } else if (isAuthenticated && inAuthGroup) {
      router.replace("/(main)/home");
    }
  }, [isAuthenticated, segments]);

  useNotifications();

  return <Slot />;
}

export default function RootLayout() {
  const [dbReady, setDbReady] = useState(false);

  useEffect(() => {
    runMigrations()
      .then(() => setDbReady(true))
      .catch(() => setDbReady(true)); // don't block app if migrations fail
  }, []);

  if (!dbReady) {
    return (
      <View className="flex-1 bg-surface-canvas items-center justify-center">
        <Text className="text-sm text-ink-muted">Starting…</Text>
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="dark" />
        <OfflineBanner />
        <SyncQueueRunner />
        <AuthGuard />
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
