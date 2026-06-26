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
import { Alert, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card, ErrorState, ScreenLoader } from "@/components/ui";
import { useCancelSubscription } from "@/features/billing/usePayment";
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
    Alert.alert(
      "Cancel subscription?",
      "You'll keep access to your current plan until the end of the billing period. After that, your account moves to Personal Basic.",
      [
        { text: "Keep subscription", style: "cancel" },
        {
          text: "Cancel subscription",
          style: "destructive",
          onPress: () => cancel(),
        },
      ]
    );
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

  const planName = PLAN_NAMES[sub.plan_id ?? ""] ?? sub.plan_id ?? "Unknown plan";
  const statusMeta = STATUS_LABELS[sub.status ?? ""] ?? STATUS_LABELS.expired;
  const periodEnd = sub.current_period_end ? formatDate(sub.current_period_end) : null;
  const isCancelling = sub.cancel_at_period_end;

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
        <View className="bg-amber-50 border border-amber-200 rounded-xl px-lg py-md flex-row items-start gap-sm">
          <AlertCircle size={16} color="#d97706" strokeWidth={2} style={{ marginTop: 2 }} />
          <Text className="text-sm text-amber-800 flex-1 leading-relaxed">
            Your subscription is set to cancel on{" "}
            <Text className="font-semibold">{periodEnd}</Text>. You'll keep
            full access until then.
          </Text>
        </View>
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
        {sub.status === "active" && !isCancelling && (
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
        <View className="bg-red-50 border border-red-200 rounded-xl px-lg py-md">
          <Text className="text-sm text-red-700">{getApiErrorMessage(cancelError)}</Text>
        </View>
      )}

      {/* Actions */}
      <View className="gap-sm">
        <Pressable
          className="bg-brand-primary rounded-xl py-md items-center justify-center flex-row gap-sm active:opacity-70"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.push("/(main)/plans" as any)}
        >
          <CreditCard size={16} color="#fff" strokeWidth={2} />
          <Text className="text-white font-semibold text-md">Change plan</Text>
        </Pressable>

        {/* Cancel button — hidden if already cancelling or subscription not active */}
        {sub.status === "active" && !isCancelling && (
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
    </ScrollView>
  );
}
