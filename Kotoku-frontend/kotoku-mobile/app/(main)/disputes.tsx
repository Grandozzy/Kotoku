import { ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card } from "@/components/ui";

export default function DisputesScreen() {
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Disputes</Text>
        <Text className="text-sm text-ink-secondary mt-xs">
          Raise or track a dispute on a sealed agreement
        </Text>
      </View>

      {/* Dispute list — populated in Phase 5 */}
      <Card elevation="sm">
        <Text className="text-sm text-ink-muted text-center py-lg">
          No disputes yet.
        </Text>
      </Card>
    </ScrollView>
  );
}
