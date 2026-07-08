import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { AlertCircle, CheckCircle2, Clock3, RefreshCw } from "lucide-react-native";
import { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";

import { Button, NoticeCard } from "@/components/ui";
import { getCheckoutStatus } from "@/api/payments";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { colors } from "@/theme/tokens";

const CONFIRMATION_TIMEOUT_MS = 45_000;

export default function PaymentCallbackScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { reference, plan_id } = useLocalSearchParams<{
    reference?: string;
    plan_id?: string;
  }>();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (!reference || timedOut) return;
    const timer = setTimeout(() => setTimedOut(true), CONFIRMATION_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [reference, timedOut]);

  const statusQuery = useQuery({
    queryKey: ["billing", "checkout-status", reference],
    queryFn: () => getCheckoutStatus(reference!),
    enabled: !!reference,
    retry: 1,
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.checkout_status;
      if (!reference || timedOut) return false;
      if (status === "succeeded" || status === "failed" || status === "cancelled") return false;
      return 2000;
    },
  });

  const checkoutStatus = statusQuery.data?.checkout_status;

  useEffect(() => {
    if (checkoutStatus !== "succeeded") return;
    queryClient.invalidateQueries({ queryKey: ["billing", "current-plan"] });
    queryClient.invalidateQueries({ queryKey: ["billing", "subscription"] });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    router.replace({
      pathname: "/(main)/payment/success" as any,
      params: {
        reference,
        plan_id: statusQuery.data?.current_plan_id ?? plan_id,
      },
    });
  }, [checkoutStatus, plan_id, queryClient, reference, router, statusQuery.data?.current_plan_id]);

  if (!reference) {
    return (
      <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
        <View className="w-20 h-20 rounded-full bg-red-50 items-center justify-center">
          <AlertCircle size={36} color={colors.error} strokeWidth={1.6} />
        </View>
        <View className="items-center gap-sm">
          <Text className="text-2xl font-semibold text-ink-primary text-center">
            Missing payment reference
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed">
            We could not confirm this payment session. Return to plans and try again if needed.
          </Text>
        </View>
        <Button
          title="Back to plans"
          variant="primary"
          size="lg"
          fullWidth
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.replace("/(main)/plans" as any)}
        />
      </View>
    );
  }

  if (checkoutStatus === "failed" || checkoutStatus === "cancelled") {
    const cancelled = checkoutStatus === "cancelled";
    return (
      <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
        <View className={`w-20 h-20 rounded-full items-center justify-center ${cancelled ? "bg-amber-50" : "bg-red-50"}`}>
          <AlertCircle size={36} color={cancelled ? "#d97706" : colors.error} strokeWidth={1.6} />
        </View>
        <View className="items-center gap-sm">
          <Text className="text-2xl font-semibold text-ink-primary text-center">
            {cancelled ? "Payment cancelled" : "Payment not confirmed"}
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed">
            {statusQuery.data?.detail ?? "This checkout did not complete successfully."}
          </Text>
          <Text className="text-xs text-ink-muted text-center">
            Reference: {reference}
          </Text>
        </View>
        <View className="w-full gap-md">
          <Button
            title="Back to plans"
            variant="primary"
            size="lg"
            fullWidth
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onPress={() => router.replace("/(main)/plans" as any)}
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

  if (timedOut) {
    return (
      <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
        <View className="w-20 h-20 rounded-full bg-amber-50 items-center justify-center">
          <Clock3 size={36} color="#d97706" strokeWidth={1.6} />
        </View>
        <View className="items-center gap-sm">
          <Text className="text-2xl font-semibold text-ink-primary text-center">
            Still confirming payment
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed">
            {statusQuery.data?.detail ?? "Your payment may still be processing. Check again in a moment."}
          </Text>
          <Text className="text-xs text-ink-muted text-center">
            Reference: {reference}
          </Text>
        </View>
        <View className="w-full gap-md">
          <Button
            title={statusQuery.isFetching ? "Checking…" : "Check again"}
            variant="primary"
            size="lg"
            fullWidth
            loading={statusQuery.isFetching}
            onPress={() => {
              setTimedOut(false);
              void statusQuery.refetch();
            }}
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

  return (
    <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
      <View className="w-24 h-24 rounded-full bg-blue-50 items-center justify-center">
        {checkoutStatus === "pending" ? (
          <Clock3 size={44} color={colors.brandPrimary} strokeWidth={1.5} />
        ) : (
          <ActivityIndicator size="large" color={colors.brandPrimary} />
        )}
      </View>

      <View className="items-center gap-sm">
        <Text className="text-2xl font-semibold text-ink-primary text-center">
          Confirming your upgrade
        </Text>
        <Text className="text-md text-ink-secondary text-center leading-relaxed">
          {statusQuery.data?.detail ?? "Your payment was received. We are updating your plan now."}
        </Text>
        <Text className="text-xs text-ink-muted text-center">
          Reference: {reference}
        </Text>
      </View>

      {!!statusQuery.error && (
        <NoticeCard
          variant="warning"
          title="Status check needs another try"
          body={getApiErrorMessage(statusQuery.error)}
        />
      )}

      <NoticeCard
        variant="info"
        icon={CheckCircle2}
        title="Do not repay"
        body="Kotoku only shows success after the backend confirms your upgraded account. One completed checkout is enough."
      />

      <Button
        title={statusQuery.isFetching ? "Checking…" : "Refresh status"}
        variant="secondary"
        size="lg"
        fullWidth
        onPress={() => void statusQuery.refetch()}
      />
    </View>
  );
}
