import { useRouter } from "expo-router";
import { AlertTriangle, FileText, Handshake, TrendingUp } from "lucide-react-native";
import { useState } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, CardSkeleton, EmptyState } from "@/components/ui";
import { usePendingActions } from "@/features/agreements/usePendingActions";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useDraftSession } from "@/hooks/useDraftSession";
import { usePlan } from "@/features/billing/usePlan";
import { SCENARIOS } from "@/constants/scenarios";
import { colors } from "@/theme/tokens";

const SCENARIO_LABELS: Record<string, string> = {};
for (const s of SCENARIOS) {
  SCENARIO_LABELS[s.id] = s.label;
}

export default function HomeScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data, isLoading, refetch } = usePendingActions();
  const { data: plan } = usePlan();

  const actionRequired = data?.action_required ?? [];
  const drafts = data?.drafts ?? [];
  const isEmpty = !isLoading && actionRequired.length === 0 && drafts.length === 0;

  const usage = plan?.usage;
  const flags = plan?.flags;
  const showUsagePill =
    plan && flags?.is_personal && usage !== undefined;
  const capReached = usage?.is_cap_reached ?? false;
  const nearCap = usage?.is_near_cap ?? false;
  const showUpgradeBanner =
    !!plan && flags?.show_upgrade_recommendation && plan.recommended_upgrades.length > 0;

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={refetch}
          tintColor={colors.brandPrimary}
        />
      }
    >
      <View className="flex-row items-center justify-between">
        <View>
          <Text className="text-2xl font-semibold text-ink-primary">Home</Text>
          {showUsagePill ? (
            <Text
              className={`text-sm mt-xs font-medium ${
                capReached
                  ? "text-semantic-error"
                  : nearCap
                  ? "text-amber-600"
                  : "text-ink-secondary"
              }`}
            >
              {capReached
                ? `Monthly limit reached (${plan.plan.name})`
                : `${usage!.remaining_agreements_this_period} agreement${
                    usage!.remaining_agreements_this_period === 1 ? "" : "s"
                  } left this month`}
            </Text>
          ) : (
            <Text className="text-sm text-ink-secondary mt-xs">
              Start or resume an agreement
            </Text>
          )}
        </View>
        <Button
          title="New"
          variant="primary"
          size="sm"
          onPress={() => router.push("/agreement/new")}
        />
      </View>

      {/* Upgrade banner — shown when cap reached or business misuse suspected */}
      {showUpgradeBanner && (
        <View className="bg-amber-50 border border-amber-200 rounded-xl px-lg py-md flex-row items-start gap-sm">
          <TrendingUp size={16} color="#d97706" strokeWidth={2} style={{ marginTop: 2 }} />
          <View className="flex-1">
            <Text className="text-sm font-semibold text-amber-800">
              {capReached
                ? `You've reached your ${plan!.plan.max_agreements_per_month} agreement limit for ${plan!.plan.name}`
                : "You're using Kotoku like a business"}
            </Text>
            <Text className="text-xs text-amber-700 mt-xs">
              {capReached
                ? "Upgrade to seal more agreements this month, or wait until next month."
                : "Switch to an Enterprise plan for higher volume, team access, and longer retention."}
            </Text>
            {plan!.recommended_upgrades[0] && (
              <Text className="text-xs font-semibold text-amber-800 mt-sm">
                Next: {plan!.recommended_upgrades[0].name} — {plan!.recommended_upgrades[0].price_amount_monthly} GHS/mo
              </Text>
            )}
          </View>
        </View>
      )}

      {isLoading && (
        <View className="gap-sm">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </View>
      )}

      {!isLoading && actionRequired.length > 0 && (
        <View className="gap-sm">
          <Text className="text-xs font-semibold text-amber-600 uppercase tracking-widest">
            Action required
          </Text>
          {actionRequired.map((item) => (
            <ActionCard key={item.id} item={item} />
          ))}
        </View>
      )}

      {!isLoading && drafts.length > 0 && (
        <View className="gap-sm">
          <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
            Drafts
          </Text>
          {drafts.map((item) => (
            <DraftCard key={item.id} item={item} />
          ))}
        </View>
      )}

      {isEmpty && (
        <EmptyState
          icon={Handshake}
          title="Your first agreement is one tap away"
          body="Seal a deal with anyone — record evidence, collect consent via SMS, and create a tamper-proof vault entry in under five minutes."
          action={{
            label: "New agreement",
            onPress: () => router.push("/agreement/new"),
          }}
        />
      )}
    </ScrollView>
  );
}

function ActionCard({ item }: { item: { id: number; title: string; status: string; scenario_template: string } }) {
  const router = useRouter();
  const initForConsent = useAgreementStore((s) => s.initForConsent);
  const { load } = useDraftSession();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePress = async () => {
    if (item.status === "pending_consent") {
      setLoading(true);
      setError(null);
      try {
        const state = await load(item.id);
        initForConsent(state.agreementId, state.scenarioId, state.partyA, state.partyB);
        router.push(`/agreement/${state.agreementId}/steps/consent?scenarioId=${state.scenarioId}`);
      } catch {
        setError("Failed to load. Try again.");
      } finally {
        setLoading(false);
      }
    } else if (item.status === "reopen_requested") {
      router.push(`/(main)/vault/${item.id}`);
    } else {
      router.push(`/agreement/${item.id}/steps/review?scenarioId=${item.scenario_template}`);
    }
  };

  const label =
    item.status === "reopen_requested"
      ? "Reopen requested — enter your code"
      : item.status === "pending_consent"
        ? "Pending your consent — enter code"
        : item.status;

  return (
    <Pressable
      onPress={handlePress}
      disabled={loading}
      className="bg-surface-card rounded-xl border border-amber-200 p-lg active:opacity-70"
    >
      <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
        {item.title}
      </Text>
      <Text className="text-sm text-amber-600 mt-xs">{label}</Text>
      {error && <Text className="text-xs text-semantic-error mt-xs">{error}</Text>}
      <Text className="text-xs text-brand-primary mt-xs">
        {loading ? "Loading…" : "Tap to continue →"}
      </Text>
    </Pressable>
  );
}

function DraftCard({ item }: { item: { id: number; title: string; updated_at: string; scenario_template: string; status: string; step_index?: number; parties?: Array<{ role: string; full_name?: string; display_name?: string; phone: string; id_type?: string; id_number?: string }> } }) {
  const router = useRouter();
  const hydrate = useAgreementStore((s) => s.hydrate);
  const { load } = useDraftSession();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePress = async () => {
    setLoading(true);
    setError(null);
    try {
      const state = await load(item.id);
      hydrate(state);
      router.push(`/agreement/${item.id}/steps/${STEPS[state.stepIndex]}?scenarioId=${state.scenarioId}`);
    } catch {
      setError("Failed to load draft. Try again.");
    } finally {
      setLoading(false);
    }
  };

  console.log("[DraftCard] item.id:", item.id, "step_index:", item.step_index, "parties:", item.parties?.length);
  const relativeTime = getRelativeTime(item.updated_at);
  const scenarioLabel = SCENARIO_LABELS[item.scenario_template] ?? item.scenario_template;
  const partyNames = item.parties?.map(p => p.full_name ?? p.display_name ?? "").filter(Boolean).join(", ");
  const stepIndex = item.step_index ?? 0;
  const totalSteps = STEPS.length;

  return (
    <Pressable
      onPress={handlePress}
      disabled={loading}
      className="bg-surface-card rounded-xl border border-border-subtle p-lg active:opacity-70"
    >
      <View className="flex-row items-start gap-md">
        <View className="w-9 h-9 rounded-lg bg-surface-canvas items-center justify-center mt-xs">
          <FileText size={16} color={colors.inkSecondary} strokeWidth={1.8} />
        </View>
        <View className="flex-1">
          <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
            {item.title}
          </Text>
          <Text className="text-xs text-ink-muted mt-xs">{scenarioLabel} · {relativeTime}</Text>
          <View className="flex-row items-center gap-sm mt-xs">
            <View className="flex-row gap-xs">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <View
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full ${i <= stepIndex ? "bg-brand-primary" : "bg-border-subtle"}`}
                />
              ))}
            </View>
            <Text className="text-xs text-ink-secondary">
              {stepIndex + 1} of {totalSteps} steps
            </Text>
          </View>
          {partyNames && <Text className="text-xs text-ink-secondary mt-xs">{partyNames}</Text>}
          {error && <Text className="text-xs text-semantic-error mt-xs">{error}</Text>}
          <Text className="text-xs text-brand-primary mt-xs">{loading ? "Loading…" : "Continue →"}</Text>
        </View>
      </View>
    </Pressable>
  );
}

function getRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
