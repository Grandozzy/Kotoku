import { AlertCircle, Lock } from "lucide-react-native";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { CardSkeleton, EmptyState } from "@/components/ui";
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
        <View className="flex-1 items-center justify-center px-2xl gap-md">
          <View className="w-14 h-14 rounded-2xl bg-semantic-error/10 items-center justify-center">
            <AlertCircle size={24} color={colors.error} strokeWidth={1.6} />
          </View>
          <Text className="text-md font-semibold text-ink-primary text-center">
            Could not load vault
          </Text>
          <Text className="text-sm text-ink-secondary text-center">
            Check your connection and pull down to retry.
          </Text>
          <Pressable onPress={() => refetch()} className="active:opacity-70">
            <Text className="text-sm text-brand-primary font-medium">Try again</Text>
          </Pressable>
        </View>
      )}

      {!isLoading && !error && records?.length === 0 && (
        <EmptyState
          icon={Lock}
          title="Your vault is empty"
          body="Sealed agreements are stored here — tamper-proof, hashed, and retrievable any time. Seal your first agreement to get started."
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
