import { useRouter } from "expo-router";
import {
  AlertCircle,
  Calendar,
  ChevronLeft,
  CreditCard,
  ReceiptText,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { BottomSheet, Button, Card, ErrorState, NoticeCard, ScreenLoader } from "@/components/ui";
import { useCancelSubscription, useRecoverPayment } from "@/features/billing/usePayment";
import { useSubscription } from "@/features/billing/useSubscription";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { colors } from "@/theme/tokens";

const PLAN_NAMES: Record<string, string> = {
  personal_basic: "Personal Basic",
  personal_plus: "Personal Plus",
  personal_protect: "Personal Protect",
  enterprise_standard: "Enterprise Standard",
  enterprise_plus: "Enterprise Plus",
};

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: "Active", color: "#16a34a", bg: "bg-green-100" },
  pending: { label: "Pending", color: "#d97706", bg: "bg-amber-100" },
  paused: { label: "Paused", color: "#64748b", bg: "bg-slate-100" },
  cancelled: { label: "Cancelled", color: "#dc2626", bg: "bg-red-100" },
  past_due: { label: "Past due", color: "#dc2626", bg: "bg-red-100" },
  expired: { label: "Expired", color: "#94a3b8", bg: "bg-slate-100" },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function SubscriptionScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: sub, isError, isLoading, refetch } = useSubscription();
  const { mutate: cancel, isPending: cancelling, error: cancelError } = useCancelSubscription();
  const { mutate: recover, isPending: recovering, error: recoveryError } = useRecoverPayment();
  const [cancelSheetVisible, setCancelSheetVisible] = useState(false);

  if (isLoading) return <ScreenLoader />;

  if (isError) {
    return (
      <View
        className="flex-1 bg-surface-canvas"
        style={{ paddingTop: insets.top }}
      >
        <ErrorState
          title="Could not load subscription"
          body="Check your connection and try again before changing or cancelling a plan."
          onAction={() => refetch()}
        />
      </View>
    );
  }

  function handleCancel() {
    setCancelSheetVisible(true);
  }

  // No active subscription
  if (!sub?.has_subscription) {
    return (
      <View
        className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl"
        style={{ paddingTop: insets.top }}
      >
        <View className="w-24 h-24 rounded-3xl bg-brand-primary/10 border border-brand-primary/20 items-center justify-center">
          <Sparkles size={42} color={colors.brandPrimary} strokeWidth={1.6} />
        </View>
        <View className="items-center gap-sm">
          <Text className="text-xl font-semibold text-ink-primary text-center">
            No active subscription
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed">
            Upgrade to a paid plan to unlock more sealed agreements per month.
          </Text>
        </View>
        <Pressable
          className="bg-brand-primary rounded-xl px-2xl py-md active:opacity-70 w-full items-center flex-row justify-center gap-sm"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.push("/(main)/plans" as any)}
        >
          <CreditCard size={16} color="#fff" strokeWidth={2} />
          <Text className="text-white font-semibold text-md">View plans</Text>
        </Pressable>
        <Pressable onPress={() => router.back()} className="active:opacity-70">
          <Text className="text-ink-secondary text-sm">Go back</Text>
        </Pressable>
      </View>
    );
  }

  const currentSub = sub!;
  const planName = PLAN_NAMES[currentSub.plan_id ?? ""] ?? currentSub.plan_id ?? "Unknown plan";
  const statusMeta = STATUS_LABELS[currentSub.status ?? ""] ?? STATUS_LABELS.expired;
  const periodEnd = currentSub.current_period_end ? formatDate(currentSub.current_period_end) : null;
  const isCancelling = currentSub.cancel_at_period_end;
  const isPastDue = currentSub.status === "past_due";

  function handleRecovery(channel: "card" | "mobile_money") {
    if (!currentSub.plan_id || recovering) return;
    recover({ planId: currentSub.plan_id, channel });
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      {/* Header */}
      <View className="flex-row items-center gap-md">
        <Pressable
          onPress={() => router.back()}
          className="w-9 h-9 rounded-lg bg-surface-card border border-border-subtle items-center justify-center active:opacity-70"
        >
          <ChevronLeft size={18} color={colors.inkSecondary} strokeWidth={1.8} />
        </Pressable>
        <Text className="text-xl font-semibold text-ink-primary">Subscription</Text>
      </View>

      {/* Cancellation warning banner */}
      {isCancelling && periodEnd && (
        <NoticeCard
          variant="warning"
          icon={AlertCircle}
          title="Cancellation scheduled"
          body={`Your subscription is set to cancel on ${periodEnd}. You'll keep full access until then.`}
        />
      )}

      {isPastDue && (
        <NoticeCard
          variant="error"
          icon={AlertCircle}
          title="Renewal payment failed"
          body="Pay now with card or Mobile Money to reactivate this subscription."
        />
      )}

      {/* Subscription details card */}
      <Card elevation="sm" padded={false}>
        {/* Plan + status */}
        <View className="px-lg py-md flex-row items-center justify-between border-b border-border-subtle">
          <View className="flex-row items-center gap-sm">
            <View className="w-9 h-9 rounded-lg bg-brand-primary/10 items-center justify-center">
              <ShieldCheck size={18} color={colors.brandPrimary} strokeWidth={1.8} />
            </View>
            <View>
              <Text className="text-md font-semibold text-ink-primary">{planName}</Text>
              <Text className="text-xs text-ink-muted">Monthly billing</Text>
            </View>
          </View>
          <View className={`px-sm py-xs rounded-full ${statusMeta.bg}`}>
            <Text className="text-xs font-semibold" style={{ color: statusMeta.color }}>
              {statusMeta.label}
            </Text>
          </View>
        </View>

        {/* Period end */}
        {periodEnd && (
          <View className="px-lg py-md flex-row items-center gap-sm border-b border-border-subtle">
            <Calendar size={16} color={colors.inkMuted} strokeWidth={1.8} />
            <View>
              <Text className="text-xs text-ink-muted">
                {isCancelling ? "Access until" : "Next renewal"}
              </Text>
              <Text className="text-sm font-medium text-ink-primary">{periodEnd}</Text>
            </View>
          </View>
        )}

        {/* Active indicator */}
        {currentSub.status === "active" && !isCancelling && (
          <View className="px-lg py-md flex-row items-center gap-sm">
            <Zap size={16} color="#16a34a" strokeWidth={2} />
            <Text className="text-sm text-green-700">
              Subscription renews automatically
            </Text>
          </View>
        )}
      </Card>

      {/* Cancel error */}
      {!!cancelError && (
        <NoticeCard
          variant="error"
          title="Could not cancel subscription"
          body={getApiErrorMessage(cancelError)}
          compact
        />
      )}

      {!!recoveryError && (
        <NoticeCard
          variant="error"
          title="Recovery payment could not start"
          body={getApiErrorMessage(recoveryError)}
          compact
        />
      )}

      {/* Actions */}
      <View className="gap-sm">
        {isPastDue && (
          <>
            <Pressable
              className={`bg-brand-primary rounded-xl py-md items-center justify-center flex-row gap-sm active:opacity-70 ${
                recovering ? "opacity-40" : ""
              }`}
              onPress={() => handleRecovery("mobile_money")}
              disabled={recovering}
            >
              <Zap size={16} color="#fff" strokeWidth={2} />
              <Text className="text-white font-semibold text-md">
                {recovering ? "Opening checkout…" : "Pay with Mobile Money"}
              </Text>
            </Pressable>

            <Pressable
              className={`rounded-xl py-md items-center border border-border-subtle active:opacity-70 ${
                recovering ? "opacity-40" : ""
              }`}
              onPress={() => handleRecovery("card")}
              disabled={recovering}
            >
              <View className="flex-row items-center justify-center gap-sm">
                <CreditCard size={16} color={colors.brandPrimary} strokeWidth={1.8} />
                <Text className="text-brand-primary text-md font-medium">Pay with card</Text>
              </View>
            </Pressable>
          </>
        )}

        <Pressable
          className="bg-brand-primary rounded-xl py-md items-center justify-center flex-row gap-sm active:opacity-70"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.push("/(main)/plans" as any)}
        >
          <CreditCard size={16} color="#fff" strokeWidth={2} />
          <Text className="text-white font-semibold text-md">Change plan</Text>
        </Pressable>

        {/* Cancel button — hidden if already cancelling or subscription not active */}
        {currentSub.status === "active" && !isCancelling && (
          <Pressable
            className={`rounded-xl py-md items-center border border-border-subtle active:opacity-70 ${
              cancelling ? "opacity-40" : ""
            }`}
            onPress={handleCancel}
            disabled={cancelling}
          >
            <View className="flex-row items-center justify-center gap-sm">
              <ReceiptText size={16} color={colors.error} strokeWidth={1.8} />
              <Text className="text-semantic-error text-md font-medium">
                {cancelling ? "Cancelling…" : "Cancel subscription"}
              </Text>
            </View>
          </Pressable>
        )}
      </View>

      <BottomSheet
        visible={cancelSheetVisible}
        onClose={() => setCancelSheetVisible(false)}
        title="Cancel subscription?"
        body="You'll keep access to your current plan until the end of the billing period. After that, your account moves to Personal Basic."
        icon={AlertCircle}
        tone="danger"
        footer={
          <>
            <Button
              title="Keep subscription"
              variant="secondary"
              size="lg"
              fullWidth
              onPress={() => setCancelSheetVisible(false)}
            />
            <Button
              title={cancelling ? "Cancelling…" : "Cancel subscription"}
              variant="primary"
              size="lg"
              fullWidth
              loading={cancelling}
              onPress={() => {
                setCancelSheetVisible(false);
                cancel();
              }}
            />
          </>
        }
      />
    </ScrollView>
  );
}
