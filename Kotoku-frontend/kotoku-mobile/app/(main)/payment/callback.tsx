import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, Text, View } from "react-native";

import { colors } from "@/theme/tokens";

export default function PaymentCallbackScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { reference, plan_id } = useLocalSearchParams<{
    reference?: string;
    plan_id?: string;
  }>();

  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ["billing", "current-plan"] });
    queryClient.invalidateQueries({ queryKey: ["billing", "subscription"] });

    const timer = setTimeout(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      router.replace({ pathname: "/(main)/payment/success" as any, params: { reference, plan_id } });
    }, 400);

    return () => clearTimeout(timer);
  }, [plan_id, queryClient, reference, router]);

  return (
    <View className="flex-1 bg-surface-canvas items-center justify-center px-lg gap-md">
      <ActivityIndicator size="large" color={colors.brandPrimary} />
      <Text className="text-lg font-semibold text-ink-primary text-center">
        Returning to Kotoku
      </Text>
      <Text className="text-sm text-ink-secondary text-center">
        Your payment is being checked. This usually takes a few seconds.
      </Text>
    </View>
  );
}
