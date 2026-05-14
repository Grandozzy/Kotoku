import "@/lib/global.css";

import * as Sentry from "@sentry/react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import {
  useFonts,
  CormorantGaramond_400Regular,
  CormorantGaramond_600SemiBold,
} from "@expo-google-fonts/cormorant-garamond";

if (process.env.EXPO_PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
    environment: process.env.EXPO_PUBLIC_API_URL?.includes("staging")
      ? "staging"
      : process.env.EXPO_PUBLIC_API_URL?.includes("localhost")
        ? "development"
        : "production",
    enabled: !process.env.EXPO_PUBLIC_API_URL?.includes("localhost"),
  });
}
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
  const [hydrated, setHydrated] = useState(false);

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
      setHydrated(true);
    })();
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const inAuthGroup = segments[0] === "(auth)";
    if (!isAuthenticated && !inAuthGroup) {
      router.replace("/(auth)/welcome");
    } else if (isAuthenticated && inAuthGroup) {
      router.replace("/(main)/home");
    }
  }, [hydrated, isAuthenticated, segments]);

  useNotifications();

  return <Slot />;
}

export default function RootLayout() {
  const [dbReady, setDbReady] = useState(false);
  const [fontsLoaded] = useFonts({
    CormorantGaramond_400Regular,
    CormorantGaramond_600SemiBold,
  });

  useEffect(() => {
    runMigrations()
      .then(() => setDbReady(true))
      .catch(() => setDbReady(true)); // don't block app if migrations fail
  }, []);

  if (!dbReady || !fontsLoaded) {
    return (
      <View className="flex-1 bg-surface-canvas items-center justify-center">
        <Text className="text-sm text-ink-muted">Starting…</Text>
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <StatusBar style="dark" />
          <OfflineBanner />
          <SyncQueueRunner />
          <AuthGuard />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
