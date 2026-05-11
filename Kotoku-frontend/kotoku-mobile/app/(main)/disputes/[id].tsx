import { ActivityIndicator, ScrollView, Text, View, Pressable } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ChevronLeft } from "lucide-react-native";

import { Card } from "@/components/ui";
import { useDisputeDetail } from "@/hooks/useDisputes";
import { colors } from "@/theme/tokens";

export default function DisputeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: dispute, isLoading, isError } = useDisputeDetail(Number(id));

  if (isLoading) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (isError || !dispute) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <Text className="text-sm text-ink-muted">Dispute not found</Text>
      </View>
    );
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      <View className="flex-row items-center mb-lg gap-md">
        <Pressable onPress={() => router.back()} className="p-sm -ml-sm">
          <ChevronLeft size={24} color={colors.inkPrimary} />
        </Pressable>
        <Text className="text-2xl font-semibold text-ink-primary">Dispute Details</Text>
      </View>

      <Card elevation="sm" className="mb-lg">
        <View className="gap-md">
          <View>
            <Text className="text-sm text-ink-muted">Agreement</Text>
            <Text className="text-base text-ink-primary">{dispute.agreement_type}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Sealed At</Text>
            <Text className="text-base text-ink-primary">
              {new Date(dispute.agreement_sealed_at).toLocaleDateString("en-GH")}
            </Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Raised By</Text>
            <Text className="text-base text-ink-primary">{dispute.raised_by_display_name}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Status</Text>
            <Text className="text-base text-ink-primary capitalize">{dispute.status}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Reason</Text>
            <Text className="text-base text-ink-primary">{dispute.reason}</Text>
          </View>
          {dispute.resolution && (
            <View>
              <Text className="text-sm text-ink-muted">Resolution</Text>
              <Text className="text-base text-ink-primary">{dispute.resolution}</Text>
            </View>
          )}
        </View>
      </Card>
    </ScrollView>
  );
}
