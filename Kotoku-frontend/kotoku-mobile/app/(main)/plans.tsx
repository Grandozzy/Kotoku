import { useRouter } from "expo-router";
import { Check, ChevronLeft, ShieldCheck, TrendingUp, Zap } from "lucide-react-native";
import { ScrollView, Text, View, Pressable, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

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
  price: number;
  sealsPerMonth: number | null; // null = unlimited
  features: string[];
}

const PLANS: PlanDefinition[] = [
  {
    id: "personal_basic",
    name: "Personal Basic",
    family: "personal",
    price: 10,
    sealsPerMonth: 1,
    features: ["1 sealed agreement / month", "Tamper-proof vault", "SMS consent delivery"],
  },
  {
    id: "personal_plus",
    name: "Personal Plus",
    family: "personal",
    price: 25,
    sealsPerMonth: 3,
    features: ["3 sealed agreements / month", "Tamper-proof vault", "SMS consent delivery", "Priority support"],
  },
  {
    id: "personal_protect",
    name: "Personal Protect",
    family: "personal",
    price: 60,
    sealsPerMonth: 10,
    features: ["10 sealed agreements / month", "Tamper-proof vault", "SMS consent delivery", "Priority support", "Extended 24-month retention"],
  },
  {
    id: "enterprise_standard",
    name: "Enterprise Standard",
    family: "enterprise",
    price: 400,
    sealsPerMonth: 30,
    features: ["30 sealed agreements / month", "Team seats", "Bulk creation", "Reporting dashboard", "36-month retention"],
  },
  {
    id: "enterprise_plus",
    name: "Enterprise Plus",
    family: "enterprise",
    price: 1200,
    sealsPerMonth: null,
    features: ["Unlimited sealed agreements", "Team seats", "Bulk creation", "Reporting dashboard", "Archive search", "48-month retention", "Dedicated support"],
  },
];

// ── Screen ───────────────────────────────────────────────────────────────────

export default function PlansScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data: plan } = usePlan();
  const { data: subscription } = useSubscription();
  const { mutate: initiate, isPending, variables: pendingPlanId, error } = useInitiatePayment();

  const currentPlanId = plan?.plan.id;
  const activePlanId = subscription?.has_subscription ? subscription.plan_id : null;

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
          <Text className="text-md font-semibold text-ink-primary">{plan.name}</Text>
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
            <View key={f} className="flex-row items-center gap-sm">
              <Check size={14} color={colors.brandPrimary} strokeWidth={2.5} />
              <Text className="text-sm text-ink-secondary flex-1">{f}</Text>
            </View>
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
