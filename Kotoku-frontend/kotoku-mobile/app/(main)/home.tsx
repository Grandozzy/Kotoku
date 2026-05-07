import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui";
import { getAgreement } from "@/api/agreements";
import { usePendingActions } from "@/features/agreements/usePendingActions";
import { useAgreementStore, type PartyDraft } from "@/features/agreements/agreementStore";
import type { ScenarioId } from "@/constants/scenarios";
import { colors } from "@/theme/tokens";

export default function HomeScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data, isLoading, refetch } = usePendingActions();

  const actionRequired = data?.action_required ?? [];
  const drafts = data?.drafts ?? [];

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
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Home</Text>
        <Text className="text-sm text-ink-secondary mt-xs">
          Start or resume an agreement
        </Text>
      </View>

      <Button
        title="New agreement"
        variant="primary"
        size="lg"
        fullWidth
        onPress={() => router.push("/agreement/new")}
      />

      {actionRequired.length > 0 && (
        <View className="gap-sm">
          <Text className="text-md font-semibold text-amber-600">
            Action required
          </Text>
          {actionRequired.map((item) => (
            <ActionCard key={item.id} item={item} />
          ))}
        </View>
      )}

      {drafts.length > 0 && (
        <View className="gap-sm">
          <Text className="text-md font-semibold text-ink-primary">Drafts</Text>
          {drafts.map((item) => (
            <DraftCard key={item.id} item={item} />
          ))}
        </View>
      )}

      {actionRequired.length === 0 && drafts.length === 0 && !isLoading && (
        <View className="items-center py-xl">
          <Text className="text-sm text-ink-muted">
            No pending actions. Tap &quot;New agreement&quot; to start.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

function ActionCard({ item }: { item: { id: number; title: string; status: string; scenario_template: string } }) {
  const router = useRouter();
  const initForConsent = useAgreementStore((s) => s.initForConsent);
  const [loading, setLoading] = useState(false);

  const handlePress = async () => {
    if (item.status === "pending_consent") {
      setLoading(true);
      try {
        const agreement = await getAgreement(item.id);
        const pA = agreement.parties[0];
        const pB = agreement.parties[1];
        initForConsent(
          agreement.id,
          agreement.scenarioId as ScenarioId,
          { fullName: pA.displayName, phone: pA.phone, idType: pA.idType ?? "ghana_card", idNumber: pA.idNumber ?? "" },
          { fullName: pB.displayName, phone: pB.phone, idType: pB.idType ?? "ghana_card", idNumber: pB.idNumber ?? "" },
        );
        router.push(`/agreement/${agreement.id}/steps/consent`);
      } catch {
      } finally {
        setLoading(false);
      }
    } else if (item.status === "reopen_requested") {
      router.push(`/(main)/vault/${item.id}`);
    } else {
      router.push(`/agreement/${item.id}/steps/review`);
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
      className="bg-surface-card rounded-lg border border-border-subtle p-lg active:opacity-70"
    >
      <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
        {item.title}
      </Text>
      <Text className="text-sm text-amber-600 mt-xs">{label}</Text>
      <Text className="text-xs text-brand-primary mt-xs">
        {loading ? "Loading…" : "Tap to continue →"}
      </Text>
    </Pressable>
  );
}

function DraftCard({ item }: { item: { id: number; title: string; updated_at: string; scenario_template: string; status: string } }) {
  const router = useRouter();
  const initDraft = useAgreementStore((s) => s.initDraft);

  const handlePress = () => {
    initDraft(item.id, item.scenario_template as ScenarioId);
    router.push(`/agreement/${item.id}/steps/${item.status === "draft" ? "parties" : "review"}`);
  };

  const relativeTime = getRelativeTime(item.updated_at);

  return (
    <Pressable
      onPress={handlePress}
      className="bg-surface-card rounded-lg border border-border-subtle p-lg active:opacity-70"
    >
      <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
        {item.title}
      </Text>
      <Text className="text-xs text-ink-muted mt-xs">{relativeTime}</Text>
      <Text className="text-xs text-brand-primary mt-xs">Continue →</Text>
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
