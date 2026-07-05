import { useRouter } from "expo-router";
import {
  Archive,
  BarChart3,
  Check,
  ChevronLeft,
  Crown,
  FileCheck2,
  Headphones,
  MessageSquareText,
  Search,
  ShieldCheck,
  TrendingUp,
  UserRound,
  UsersRound,
  Zap,
} from "lucide-react-native";
import { ScrollView, Text, View, Pressable, ActivityIndicator, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ErrorState } from "@/components/ui";
import { usePlan } from "@/features/billing/usePlan";
import { useSubscription } from "@/features/billing/useSubscription";
import { useInitiatePayment } from "@/features/billing/usePayment";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { colors } from "@/theme/tokens";

// ── Static plan catalogue ────────────────────────────────────────────────────
// Mirrors the backend PLAN_MAP. Price in GHS/month.

type PlanFamily = "personal" | "enterprise";

interface PlanDefinition {
  id: string;
  name: string;
  family: PlanFamily;
  icon: typeof ShieldCheck;
  price: number;
  sealsPerMonth: number | null; // null = unlimited
  features: string[];
}

const PLANS: PlanDefinition[] = [
  {
    id: "personal_basic",
    name: "Personal Basic",
    family: "personal",
    icon: UserRound,
    price: 49,
    sealsPerMonth: 1,
    features: ["1 sealed agreement / month", "Tamper-proof vault", "SMS consent delivery"],
  },
  {
    id: "personal_plus",
    name: "Personal Plus",
    family: "personal",
    icon: Zap,
    price: 79,
    sealsPerMonth: 3,
    features: ["3 sealed agreements / month", "Tamper-proof vault", "SMS consent delivery", "Priority support"],
  },
  {
    id: "personal_protect",
    name: "Personal Protect",
    family: "personal",
    icon: ShieldCheck,
    price: 99,
    sealsPerMonth: 7,
    features: ["7 sealed agreements / month", "Tamper-proof vault", "SMS consent delivery", "Priority support", "Extended 36-month retention"],
  },
  {
    id: "enterprise_standard",
    name: "Enterprise Standard",
    family: "enterprise",
    icon: UsersRound,
    price: 400,
    sealsPerMonth: 20,
    features: ["20 sealed agreements / month", "Team seats", "Bulk creation", "Reporting dashboard", "5-year retention"],
  },
  {
    id: "enterprise_plus",
    name: "Enterprise Plus",
    family: "enterprise",
    icon: Crown,
    price: 1200,
    sealsPerMonth: 80,
    features: ["80 sealed agreements / month", "Team seats", "Bulk creation", "Reporting dashboard", "Archive search", "10-year retention", "Dedicated support"],
  },
];

// ── Screen ───────────────────────────────────────────────────────────────────

function getFeatureIcon(feature: string) {
  const text = feature.toLowerCase();
  if (text.includes("sms")) return MessageSquareText;
  if (text.includes("vault") || text.includes("tamper")) return ShieldCheck;
  if (text.includes("team")) return UsersRound;
  if (text.includes("bulk")) return FileCheck2;
  if (text.includes("report")) return BarChart3;
  if (text.includes("archive") || text.includes("retention")) return Archive;
  if (text.includes("search")) return Search;
  if (text.includes("support")) return Headphones;
  return Check;
}

export default function PlansScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const {
    data: plan,
    isError: planError,
    isFetching: planFetching,
    refetch: refetchPlan,
  } = usePlan();
  const {
    data: subscription,
    isError: subscriptionError,
    isFetching: subscriptionFetching,
    refetch: refetchSubscription,
  } = useSubscription();
  const { mutate: initiate, isPending, variables: pendingPlanId, error } = useInitiatePayment();

  const currentPlanId = plan?.plan.id;
  const activePlanId = subscription?.has_subscription ? subscription.plan_id : null;

  const hasLoadError = planError || subscriptionError;
  const refreshing = planFetching || subscriptionFetching;
  const handleRefresh = () => {
    void refetchPlan();
    void refetchSubscription();
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          tintColor={colors.brandPrimary}
        />
      }
    >
      {/* Header */}
      <View className="flex-row items-center gap-md">
        <Pressable
          onPress={() => router.back()}
          className="w-9 h-9 rounded-lg bg-surface-card border border-border-subtle items-center justify-center active:opacity-70"
        >
          <ChevronLeft size={18} color={colors.inkSecondary} strokeWidth={1.8} />
        </Pressable>
        <View>
          <Text className="text-xl font-semibold text-ink-primary">Choose a plan</Text>
          <Text className="text-sm text-ink-secondary">Billed monthly · Cancel any time</Text>
        </View>
      </View>

      {/* Error banner */}
      {!!error && (
        <View className="bg-red-50 border border-red-200 rounded-xl px-lg py-md">
          <Text className="text-sm text-red-700">{getApiErrorMessage(error)}</Text>
        </View>
      )}

      {hasLoadError && (
        <ErrorState
          title="Could not load billing status"
          body="Plans are still shown below, but your current plan may be out of date. Refresh before starting payment."
          onAction={handleRefresh}
        />
      )}

      {/* Personal plans */}
      <View className="gap-sm">
        <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
          Personal
        </Text>
        {PLANS.filter((p) => p.family === "personal").map((p) => (
          <PlanCard
            key={p.id}
            plan={p}
            isCurrent={p.id === currentPlanId}
            isActive={p.id === activePlanId}
            isLoading={isPending && pendingPlanId === p.id}
            disabled={isPending || p.id === currentPlanId}
            onPress={() => initiate(p.id)}
          />
        ))}
      </View>

      {/* Enterprise plans */}
      <View className="gap-sm">
        <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
          Enterprise
        </Text>
        {PLANS.filter((p) => p.family === "enterprise").map((p) => (
          <PlanCard
            key={p.id}
            plan={p}
            isCurrent={p.id === currentPlanId}
            isActive={p.id === activePlanId}
            isLoading={isPending && pendingPlanId === p.id}
            disabled={isPending || p.id === currentPlanId}
            onPress={() => initiate(p.id)}
          />
        ))}
      </View>

      <Text className="text-xs text-ink-muted text-center px-lg">
        Payments are processed securely by Paystack. Your plan is activated
        immediately after payment is confirmed.
      </Text>
    </ScrollView>
  );
}

// ── PlanCard component ───────────────────────────────────────────────────────

function PlanCard({
  plan,
  isCurrent,
  isActive,
  isLoading,
  disabled,
  onPress,
}: {
  plan: PlanDefinition;
  isCurrent: boolean;
  isActive: boolean;
  isLoading: boolean;
  disabled: boolean;
  onPress: () => void;
}) {
  const isPopular = plan.id === "personal_plus";
  const PlanIcon = plan.icon;

  return (
    <View
      className={`rounded-2xl border overflow-hidden ${
        isCurrent
          ? "border-brand-primary bg-brand-primary/5"
          : isActive
          ? "border-green-400 bg-green-50"
          : "border-border-subtle bg-surface-card"
      }`}
    >
      {/* Popular badge */}
      {isPopular && !isCurrent && (
        <View className="bg-brand-primary px-lg py-xs flex-row items-center gap-xs">
          <TrendingUp size={12} color="#fff" strokeWidth={2} />
          <Text className="text-xs font-semibold text-white">Most popular</Text>
        </View>
      )}

      {/* Current / active badge */}
      {isCurrent && (
        <View className="bg-brand-primary/10 px-lg py-xs flex-row items-center gap-xs">
          <ShieldCheck size={12} color={colors.brandPrimary} strokeWidth={2} />
          <Text className="text-xs font-semibold text-brand-primary">Your current plan</Text>
        </View>
      )}
      {!isCurrent && isActive && (
        <View className="bg-green-100 px-lg py-xs flex-row items-center gap-xs">
          <Zap size={12} color="#16a34a" strokeWidth={2} />
          <Text className="text-xs font-semibold text-green-700">Active subscription</Text>
        </View>
      )}

      <View className="px-lg py-md gap-md">
        {/* Name + price */}
        <View className="flex-row items-start justify-between">
          <View className="flex-row items-center gap-sm flex-1 pr-md">
            <View className="w-10 h-10 rounded-xl bg-brand-primary/10 items-center justify-center">
              <PlanIcon size={20} color={colors.brandPrimary} strokeWidth={1.9} />
            </View>
            <View className="flex-1">
              <Text className="text-md font-semibold text-ink-primary">{plan.name}</Text>
              <Text className="text-xs text-ink-muted capitalize">{plan.family}</Text>
            </View>
          </View>
          <View className="items-end">
            <Text className="text-lg font-bold text-ink-primary">
              {plan.price} <Text className="text-sm font-normal text-ink-secondary">GHS</Text>
            </Text>
            <Text className="text-xs text-ink-muted">/ month</Text>
          </View>
        </View>

        {/* Seal count callout */}
        <View className="bg-surface-canvas rounded-xl px-md py-sm">
          <Text className="text-sm font-semibold text-ink-primary">
            {plan.sealsPerMonth === null
              ? "Unlimited sealed agreements"
              : `${plan.sealsPerMonth} sealed agreement${plan.sealsPerMonth === 1 ? "" : "s"} / month`}
          </Text>
        </View>

        {/* Features */}
        <View className="gap-xs">
          {plan.features.map((f) => (
            <FeatureRow key={f} label={f} />
          ))}
        </View>

        {/* CTA */}
        {!isCurrent && (
          <Pressable
            onPress={onPress}
            disabled={disabled}
            className={`rounded-xl py-md items-center justify-center ${
              disabled && !isLoading ? "opacity-40" : "active:opacity-70"
            } ${isActive ? "bg-green-600" : "bg-brand-primary"}`}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text className="text-white font-semibold text-md">
                {isActive ? "Switch plan" : "Upgrade to " + plan.name}
              </Text>
            )}
          </Pressable>
        )}
      </View>
    </View>
  );
}

function FeatureRow({ label }: { label: string }) {
  const FeatureIcon = getFeatureIcon(label);
  return (
    <View className="flex-row items-center gap-sm">
      <FeatureIcon size={14} color={colors.brandPrimary} strokeWidth={2.2} />
      <Text className="text-sm text-ink-secondary flex-1">{label}</Text>
    </View>
  );
}
