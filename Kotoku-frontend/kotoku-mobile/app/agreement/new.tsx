import { useRouter } from "expo-router";
import { ChevronRight, TrendingUp } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";

import { SCENARIOS } from "@/constants/scenarios";
import { useCreateDraft } from "@/features/agreements/useAgreementDraft";
import { usePlan } from "@/features/billing/usePlan";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { colors } from "@/theme/tokens";

export default function NewAgreementScreen() {
  const router = useRouter();
  const mutation = useCreateDraft();
  const { data: plan } = usePlan();

  const capReached = plan?.flags.is_personal && plan?.usage.is_cap_reached;

  if (capReached) {
    const planName = plan!.plan.name;
    const cap = plan!.plan.max_agreements_per_month;
    const upgrade = plan!.recommended_upgrades[0];

    return (
      <View className="flex-1 bg-surface-canvas px-lg py-xl gap-xl justify-center">
        <View className="bg-amber-50 border border-amber-200 rounded-2xl p-xl gap-md">
          <View className="w-12 h-12 rounded-xl bg-amber-100 items-center justify-center">
            <TrendingUp size={22} color="#d97706" strokeWidth={2} />
          </View>

          <View className="gap-xs">
            <Text className="text-lg font-semibold text-amber-900">
              Monthly limit reached
            </Text>
            <Text className="text-sm text-amber-700 leading-relaxed">
              You&apos;ve used all {cap} seal{cap === 1 ? "" : "s"} for this month on{" "}
              <Text className="font-semibold">{planName}</Text>.
              {"\n\n"}Unused seals don&apos;t roll over. Upgrade to unlock more seals now,
              or come back next month.
            </Text>
          </View>

          {upgrade && (
            <View className="bg-white rounded-xl border border-amber-200 p-md gap-xs">
              <Text className="text-xs text-amber-600 font-semibold uppercase tracking-widest">
                Recommended
              </Text>
              <Text className="text-md font-semibold text-ink-primary">
                {upgrade.name}
              </Text>
              <Text className="text-sm text-ink-secondary">
                Up to {upgrade.max_agreements_per_month} seals / month
              </Text>
              <Text className="text-md font-bold text-brand-primary">
                {upgrade.price_amount_monthly} GHS / month
              </Text>
            </View>
          )}

          <View className="gap-sm">
            {upgrade && (
              <Pressable
                className="bg-brand-primary rounded-xl py-md items-center active:opacity-70"
                onPress={() => {
                  // Deep link to pricing page — handled by web or future in-app billing screen
                  router.back();
                }}
              >
                <Text className="text-white font-semibold text-md">
                  View upgrade options
                </Text>
              </Pressable>
            )}
            <Pressable
              className="rounded-xl py-md items-center border border-border-subtle active:opacity-70"
              onPress={() => router.back()}
            >
              <Text className="text-ink-secondary text-md">
                Wait until next month
              </Text>
            </Pressable>
          </View>
        </View>
      </View>
    );
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
    >
      {/* Subtitle */}
      <Text className="text-md text-ink-secondary">
        Select the type that best matches your transaction.
      </Text>

      {/* Scenario cards */}
      {SCENARIOS.map((scenario) => (
        <Pressable
          key={scenario.id}
          disabled={mutation.isPending}
          onPress={() => mutation.mutate(scenario.id)}
          className="bg-surface-card rounded-lg p-lg border border-border-subtle flex-row items-center justify-between active:opacity-70"
        >
          <View className="flex-1 gap-xs pr-md">
            <Text className="text-md font-semibold text-ink-primary">
              {scenario.label}
            </Text>
            <Text className="text-sm text-ink-secondary">
              {scenario.shortDescription}
            </Text>
          </View>
          <ChevronRight size={20} color={colors.inkMuted} />
        </Pressable>
      ))}

      {mutation.isError && (
        <Text className="text-sm text-semantic-error text-center">
          {getApiErrorMessage(mutation.error)}
        </Text>
      )}

      {mutation.isPending && (
        <Text className="text-sm text-ink-muted text-center">
          Creating draft…
        </Text>
      )}
    </ScrollView>
  );
}
