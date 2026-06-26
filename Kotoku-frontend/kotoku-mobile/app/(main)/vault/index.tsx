import { Lock } from "lucide-react-native";
import { FlatList, RefreshControl, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { CardSkeleton, EmptyState, ErrorState } from "@/components/ui";
import { VaultCard } from "@/components/vault/VaultCard";
import { useVaultList } from "@/features/vault/useVault";
import { colors } from "@/theme/tokens";

export default function VaultScreen() {
  const { data: records, isLoading, error, refetch } = useVaultList();
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
        <View className="px-lg gap-sm">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </View>
      )}

      {error && !isLoading && (
        <ErrorState
          title="Could not load vault"
          body="Check your connection and try again. Your sealed agreements remain safe in the vault."
          onAction={() => refetch()}
        />
      )}

      {!isLoading && !error && records?.length === 0 && (
        <EmptyState
          icon={Lock}
          title="Your vault is empty"
          body="Sealed agreements are stored here. They are tamper-proof, hashed, and retrievable any time. Seal your first agreement to get started."
        />
      )}

      {!isLoading && !error && (records?.length ?? 0) > 0 && (
        <FlatList
          data={records ?? []}
          keyExtractor={(r) => String(r.id)}
          contentContainerClassName="px-lg gap-md pb-2xl"
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={refetch}
              tintColor={colors.brandPrimary}
            />
          }
          renderItem={({ item }) => (
            <VaultCard record={item} title={item.title} scenarioLabel="Sealed Agreement" />
          )}
        />
      )}
    </View>
  );
}
