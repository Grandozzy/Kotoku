import { ChevronRight, Scale } from "lucide-react-native";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { CardSkeleton, EmptyState, ErrorState, NoticeCard } from "@/components/ui";
import { useDisputes } from "@/hooks/useDisputes";
import { colors } from "@/theme/tokens";

const STATUS_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  open:     { bg: "bg-semantic-warning/15", text: "text-semantic-warning", label: "Open" },
  resolved: { bg: "bg-semantic-success/15", text: "text-semantic-success", label: "Resolved" },
  closed:   { bg: "bg-ink-muted/15",        text: "text-ink-muted",        label: "Closed" },
};

export default function DisputesIndexScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: disputes = [], isError, isLoading, refetch } = useDisputes();

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
      <View className="gap-md">
        <View className="bg-brand-primary/10 border border-brand-primary/15 rounded-3xl p-lg gap-sm">
          <View className="w-12 h-12 rounded-2xl bg-white/80 items-center justify-center">
            <Scale size={22} color={colors.brandPrimary} />
          </View>
          <View className="gap-xs">
            <Text className="text-2xl font-semibold text-ink-primary">Disputes</Text>
            <Text className="text-sm leading-relaxed text-ink-secondary">
              Track formal disputes linked to sealed agreements and keep the final
              resolution attached to the record.
            </Text>
          </View>
        </View>

        <NoticeCard
          variant="info"
          title="Disputes belong to sealed agreements"
          body="Open the agreement from your Vault if you need to review the sealed record before raising or following up on a dispute."
        />
      </View>

      {isLoading && (
        <View className="gap-sm">
          <CardSkeleton />
          <CardSkeleton />
        </View>
      )}

      {isError && !isLoading && (
        <ErrorState
          title="Could not load disputes"
          body="Check your connection and try again. Existing dispute records will appear once Kotoku reconnects."
          onAction={() => refetch()}
        />
      )}

      {!isLoading && !isError && disputes.length === 0 && (
        <EmptyState
          icon={Scale}
          title="No disputes raised"
          body="If you have a concern about a sealed agreement, open the agreement from your Vault and raise a dispute. It will be stored permanently with the sealed record."
        />
      )}

      {!isLoading && !isError && disputes.length > 0 && (
        <View className="gap-sm">
          {disputes.map((item) => {
            const config = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.closed;
            return (
              <Pressable
                key={item.id}
                onPress={() => router.push(`/disputes/${item.id}`)}
                className="bg-surface-card rounded-2xl border border-border-subtle p-lg gap-md active:opacity-70"
              >
                <View className="flex-row justify-between items-start gap-md">
                  <View className="flex-1 gap-sm">
                    <View className="w-11 h-11 rounded-2xl bg-brand-primary/10 items-center justify-center">
                      <Scale size={18} color={colors.brandPrimary} />
                    </View>
                    <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
                      {item.agreement_type || "Agreement"}
                    </Text>
                    <Text className="text-sm text-ink-secondary">
                      Raised by {item.raised_by_display_name}
                    </Text>
                  </View>
                  <View className="items-end gap-sm">
                    <View className={`px-sm py-xs rounded-full ${config.bg}`}>
                      <Text className={`text-xs font-semibold ${config.text}`}>
                        {config.label}
                      </Text>
                    </View>
                    <ChevronRight size={18} color={colors.inkMuted} />
                  </View>
                </View>
              </Pressable>
            );
          })}
        </View>
      )}
    </ScrollView>
  );
}
