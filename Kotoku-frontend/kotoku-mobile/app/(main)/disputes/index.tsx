import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card } from "@/components/ui";
import { useDisputes, type Dispute } from "@/hooks/useDisputes";

function statusStyle(status: Dispute["status"]) {
  switch (status) {
    case "open":
      return { bg: "bg-warning/20", text: "text-warning" };
    case "resolved":
      return { bg: "bg-success/20", text: "text-success" };
    default:
      return { bg: "bg-ink-muted/20", text: "text-ink-muted" };
  }
}

export default function DisputesIndexScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: disputes = [], isLoading } = useDisputes();

  if (isLoading) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <ActivityIndicator size="large" />
      </View>
    );
  }

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

      {disputes.length === 0 ? (
        <Card elevation="sm">
          <Text className="text-sm text-ink-muted text-center py-lg">No disputes yet.</Text>
        </Card>
      ) : (
        <View className="gap-sm">
          {disputes.map((item) => {
            const style = statusStyle(item.status);
            return (
              <Pressable
                key={item.id}
                onPress={() => router.push(`/disputes/${item.id}`)}
                className="active:opacity-70"
              >
                <Card elevation="sm">
                  <View className="flex-row justify-between items-center">
                    <View className="flex-1 mr-md">
                      <Text className="text-base font-medium text-ink-primary">
                        {item.agreement_type || "Agreement"}
                      </Text>
                      <Text className="text-sm text-ink-secondary">
                        Raised by {item.raised_by_display_name}
                      </Text>
                    </View>
                    <View className={`px-sm py-xs rounded ${style.bg}`}>
                      <Text className={`text-xs font-medium capitalize ${style.text}`}>
                        {item.status}
                      </Text>
                    </View>
                  </View>
                </Card>
              </Pressable>
            );
          })}
        </View>
      )}
    </ScrollView>
  );
}
