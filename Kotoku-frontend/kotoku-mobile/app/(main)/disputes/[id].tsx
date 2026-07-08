import { AlertCircle, ChevronLeft } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card, EmptyState, NoticeCard, ScreenLoader } from "@/components/ui";
import { useDisputeDetail } from "@/hooks/useDisputes";
import { colors } from "@/theme/tokens";

const STATUS_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  open:         { bg: "bg-semantic-warning/15", text: "text-semantic-warning", label: "Open" },
  under_review: { bg: "bg-blue-100",            text: "text-blue-700",         label: "Under review" },
  resolved:     { bg: "bg-semantic-success/15", text: "text-semantic-success", label: "Resolved" },
  closed:       { bg: "bg-ink-muted/15",        text: "text-ink-muted",        label: "Closed" },
};

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View className="gap-xs">
      <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
        {label}
      </Text>
      <Text className="text-md text-ink-primary leading-relaxed">{value}</Text>
    </View>
  );
}

export default function DisputeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: dispute, isLoading, isError, refetch } = useDisputeDetail(Number(id));

  if (isLoading) return <ScreenLoader rows={4} />;

  if (isError || !dispute) {
    return (
      <View className="flex-1 bg-surface-canvas" style={{ paddingTop: insets.top + 12 }}>
        <Pressable onPress={() => router.back()} className="px-lg py-sm flex-row items-center gap-sm active:opacity-70">
          <ChevronLeft size={20} color={colors.inkSecondary} strokeWidth={1.8} />
          <Text className="text-sm text-ink-secondary">Back</Text>
        </Pressable>
        <EmptyState
          icon={AlertCircle}
          title="Could not load dispute"
          body="Check your connection and try again."
          action={{ label: "Retry", onPress: () => refetch() }}
        />
      </View>
    );
  }

  const config = STATUS_CONFIG[dispute.status] ?? STATUS_CONFIG.closed;

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      <View className="gap-md">
        <View className="flex-row items-center gap-md">
          <Pressable onPress={() => router.back()} className="p-sm -ml-sm active:opacity-70">
            <ChevronLeft size={24} color={colors.inkPrimary} strokeWidth={1.8} />
          </Pressable>
          <Text className="text-2xl font-semibold text-ink-primary flex-1">Dispute</Text>
          <View className={`px-md py-xs rounded-full ${config.bg}`}>
            <Text className={`text-xs font-semibold ${config.text}`}>{config.label}</Text>
          </View>
        </View>

        <View className="bg-surface-card rounded-3xl border border-border-subtle p-lg gap-md">
          <View className="w-12 h-12 rounded-2xl bg-brand-primary/10 items-center justify-center">
            <AlertCircle size={22} color={colors.brandPrimary} />
          </View>
          <View className="gap-xs">
            <Text className="text-lg font-semibold text-ink-primary">
              {dispute.agreement_type}
            </Text>
            <Text className="text-sm leading-relaxed text-ink-secondary">
              Raised by {dispute.raised_by_display_name}. Kotoku keeps the dispute
              reason and any final resolution attached to the sealed agreement record.
            </Text>
          </View>
        </View>
      </View>

      <Card elevation="sm">
        <View className="gap-lg">
          <DetailRow label="Agreement" value={dispute.agreement_type} />
          <View className="h-px bg-border-subtle" />
          <DetailRow
            label="Sealed"
            value={new Date(dispute.agreement_sealed_at).toLocaleDateString("en-GH", {
              day: "numeric", month: "long", year: "numeric",
            })}
          />
          <View className="h-px bg-border-subtle" />
          <DetailRow label="Raised by" value={dispute.raised_by_display_name} />
        </View>
      </Card>

      <View className="gap-sm">
        <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
          Reason
        </Text>
        <Card elevation="sm">
          <Text className="text-md text-ink-primary leading-relaxed">{dispute.reason}</Text>
        </Card>
      </View>

      {dispute.resolution && (
        <NoticeCard
          variant="success"
          title="Resolution"
          body={dispute.resolution}
          footer={
            dispute.resolved_at
              ? `Resolved ${new Date(dispute.resolved_at).toLocaleDateString("en-GH", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}`
              : undefined
          }
        />
      )}
    </ScrollView>
  );
}
