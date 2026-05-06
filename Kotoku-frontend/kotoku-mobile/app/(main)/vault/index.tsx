import { FlatList, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card } from "@/components/ui";
import { VaultCard } from "@/components/vault/VaultCard";
import { useVaultList } from "@/features/vault/useVault";

export default function VaultScreen() {
  const { data: records, isLoading, error } = useVaultList();
  const insets = useSafeAreaInsets();

  return (
    <View className="flex-1 bg-surface-canvas">
      <View className="px-lg pb-md" style={{ paddingTop: insets.top + 12 }}>
        <Text className="text-2xl font-semibold text-ink-primary">Vault</Text>
        <Text className="text-sm text-ink-secondary mt-xs">
          Your sealed agreements
        </Text>
      </View>

      {isLoading && (
        <View className="px-lg">
          <Card elevation="sm">
            <Text className="text-sm text-ink-muted text-center py-lg">
              Loading…
            </Text>
          </Card>
        </View>
      )}

      {error && (
        <View className="px-lg">
          <Card elevation="sm">
            <Text className="text-sm text-semantic-error text-center py-lg">
              Could not load vault. Check your connection.
            </Text>
          </Card>
        </View>
      )}

      {!isLoading && !error && records?.length === 0 && (
        <View className="px-lg">
          <Card elevation="sm">
            <Text className="text-sm text-ink-muted text-center py-lg">
              Sealed agreements will appear here.
            </Text>
          </Card>
        </View>
      )}

      <FlatList
        data={records ?? []}
        keyExtractor={(r) => String(r.id)}
        contentContainerClassName="px-lg gap-md pb-2xl"
        renderItem={({ item }) => (
          <VaultCard record={item} title={item.title} scenarioLabel="Sealed Agreement" />
        )}
      />
    </View>
  );
}
