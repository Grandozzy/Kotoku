import { useLocalSearchParams, useRouter } from "expo-router";
import { CreditCard, LockKeyhole, X } from "lucide-react-native";
import { useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import WebView, { type WebViewNavigation } from "react-native-webview";
import type { ShouldStartLoadRequest } from "react-native-webview/lib/WebViewTypes";

import { colors } from "@/theme/tokens";

const CALLBACK_SCHEME = "kotoku://payment/callback";

export default function CheckoutScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { authorization_url, reference, plan_id } = useLocalSearchParams<{
    authorization_url: string;
    reference: string;
    plan_id: string;
  }>();

  const [loading, setLoading] = useState(true);
  const handledRef = useRef(false);

  function handleCancel() {
    Alert.alert(
      "Cancel payment?",
      "Your plan won't change if you leave now.",
      [
        { text: "Stay", style: "cancel" },
        {
          text: "Leave",
          style: "destructive",
          onPress: () => router.back(),
        },
      ]
    );
  }

  // onShouldStartLoadWithRequest fires BEFORE the WebView attempts the load
  // and returns false to block it — required on Android to prevent a load error
  // when Paystack redirects to the kotoku:// deep link scheme.
  function handleShouldStartLoadWithRequest(request: ShouldStartLoadRequest): boolean {
    if (!request.url.startsWith("kotoku://")) return true;

    if (handledRef.current) return false;
    handledRef.current = true;

    if (request.url.startsWith(CALLBACK_SCHEME)) {
      // Payment completed — navigate to success screen.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      router.replace({ pathname: "/(main)/payment/success" as any, params: { reference, plan_id } });
    } else {
      // Unexpected kotoku:// URL — treat as cancellation.
      router.back();
    }

    return false; // always block the WebView from loading custom scheme URLs
  }

  // Fallback for iOS where onShouldStartLoadWithRequest may fire differently
  function handleNavigationStateChange(state: WebViewNavigation) {
    if (!state.url.startsWith("kotoku://") || handledRef.current) return;
    handledRef.current = true;

    if (state.url.startsWith(CALLBACK_SCHEME)) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      router.replace({ pathname: "/(main)/payment/success" as any, params: { reference, plan_id } });
    } else {
      router.back();
    }
  }

  if (!authorization_url) {
    return (
      <View className="flex-1 bg-surface-canvas items-center justify-center px-lg">
        <View className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-100 items-center justify-center mb-lg">
          <CreditCard size={30} color="#d97706" strokeWidth={1.8} />
        </View>
        <Text className="text-md text-ink-secondary text-center">
          Payment session expired. Please try again.
        </Text>
        <Pressable
          className="mt-lg bg-brand-primary rounded-xl px-xl py-md active:opacity-70"
          onPress={() => router.back()}
        >
          <Text className="text-white font-semibold">Go back</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-surface-canvas" style={{ paddingTop: insets.top }}>
      {/* Header */}
      <View className="flex-row items-center justify-between px-lg py-md border-b border-border-subtle bg-surface-card">
        <View className="flex-row items-center gap-sm">
          <View className="w-9 h-9 rounded-lg bg-brand-primary/10 items-center justify-center">
            <LockKeyhole size={18} color={colors.brandPrimary} strokeWidth={1.8} />
          </View>
          <View>
            <Text className="text-md font-semibold text-ink-primary">Secure checkout</Text>
            <Text className="text-xs text-ink-muted">Powered by Paystack</Text>
          </View>
        </View>
        <Pressable
          onPress={handleCancel}
          className="w-9 h-9 rounded-lg bg-surface-canvas items-center justify-center active:opacity-70"
        >
          <X size={18} color={colors.inkSecondary} strokeWidth={1.8} />
        </Pressable>
      </View>

      {/* Loading overlay — shown until WebView reports onLoad */}
      {loading && (
        <View className="absolute inset-0 items-center justify-center bg-surface-canvas z-10">
          <ActivityIndicator size="large" color={colors.brandPrimary} />
          <Text className="text-sm text-ink-muted mt-md">Loading secure payment…</Text>
        </View>
      )}

      <WebView
        source={{ uri: authorization_url }}
        onLoad={() => setLoading(false)}
        onShouldStartLoadWithRequest={handleShouldStartLoadWithRequest}
        onNavigationStateChange={handleNavigationStateChange}
        onError={() => {
          Alert.alert(
            "Connection error",
            "Could not load the payment page. Please check your connection and try again.",
            [{ text: "OK", onPress: () => router.back() }]
          );
        }}
        originWhitelist={["https://*", "http://*", "kotoku://*"]}
        startInLoadingState={false}
        javaScriptEnabled
        domStorageEnabled
      />
    </View>
  );
}
