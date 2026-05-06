import { useRouter } from "expo-router";
import { ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Card } from "@/components/ui";

export default function HomeScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      {/* Header */}
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Home</Text>
        <Text className="text-sm text-ink-secondary mt-xs">
          Start or resume an agreement
        </Text>
      </View>

      {/* Primary action */}
      <Button
        title="New agreement"
        variant="primary"
        size="lg"
        fullWidth
        onPress={() => router.push("/agreement/new")}
      />

      {/* Drafts section — populated in Phase 4 */}
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">Drafts</Text>
        <Card elevation="sm">
          <Text className="text-sm text-ink-muted text-center py-lg">
            No drafts yet. Tap "New agreement" to start.
          </Text>
        </Card>
      </View>

      {/* Pending signatures — populated in Phase 4 */}
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Pending signatures
        </Text>
        <Card elevation="sm">
          <Text className="text-sm text-ink-muted text-center py-lg">
            No agreements waiting for your signature.
          </Text>
        </Card>
      </View>
    </ScrollView>
  );
}
