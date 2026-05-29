import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircle, Zap } from "lucide-react-native";
import { useEffect } from "react";
import { Text, View } from "react-native";

import { Button } from "@/components/ui";
import { colors } from "@/theme/tokens";

// Plan ID → display name map for the confirmation message.
const PLAN_NAMES: Record<string, string> = {
  personal_basic: "Personal Basic",
  personal_plus: "Personal Plus",
  personal_protect: "Personal Protect",
  enterprise_standard: "Enterprise Standard",
  enterprise_plus: "Enterprise Plus",
};

export default function PaymentSuccessScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { plan_id } = useLocalSearchParams<{ plan_id: string }>();

  const planName = PLAN_NAMES[plan_id ?? ""] ?? "your new plan";

  // Invalidate billing queries immediately so the plan badge and usage cap
  // reflect the new plan as soon as the user navigates home.
  // The backend processes the webhook asynchronously, so the plan may take
  // a few seconds to update — the stale time ensures a fresh fetch on next focus.
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ["billing", "current-plan"] });
    queryClient.invalidateQueries({ queryKey: ["billing", "subscription"] });
  }, [queryClient]);

  return (
    <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
      <View className="w-24 h-24 rounded-full bg-green-100 items-center justify-center">
        <CheckCircle size={52} color={colors.success} strokeWidth={1.5} />
      </View>

      <View className="items-center gap-sm">
        <Text className="text-2xl font-semibold text-ink-primary text-center">
          Payment received
        </Text>
        <Text className="text-md text-ink-secondary text-center leading-relaxed">
          Your <Text className="font-semibold text-ink-primary">{planName}</Text> subscription
          is being activated. This usually takes a few seconds.
        </Text>
      </View>

      {/* Activation note */}
      <View className="bg-green-50 border border-green-200 rounded-2xl px-lg py-md flex-row items-start gap-sm w-full">
        <Zap size={16} color="#16a34a" strokeWidth={2} style={{ marginTop: 2 }} />
        <Text className="text-sm text-green-800 flex-1 leading-relaxed">
          You'll see your updated plan and new seal limit as soon as activation
          is confirmed. Pull to refresh on the home screen if it hasn't updated yet.
        </Text>
      </View>

      <View className="w-full gap-md">
        <Button
          title="Go to home"
          variant="primary"
          size="lg"
          fullWidth
          onPress={() => router.replace("/(main)/home")}
        />
        <Button
          title="View subscription"
          variant="secondary"
          size="lg"
          fullWidth
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.replace("/(main)/subscription" as any)}
        />
      </View>
    </View>
  );
}
