import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";

import { SCENARIOS } from "@/constants/scenarios";
import { useCreateDraft } from "@/features/agreements/useAgreementDraft";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { colors } from "@/theme/tokens";

export default function NewAgreementScreen() {
  const router = useRouter();
  const mutation = useCreateDraft();
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="pb-2xl"
    >
      {/* Header */}
      <View className="flex-row items-center px-lg pb-md gap-md" style={{ paddingTop: insets.top + 12 }}>
        <Pressable onPress={() => router.back()}>
          <ChevronLeft size={24} color={colors.inkPrimary} />
        </Pressable>
        <Text className="text-xl font-semibold text-ink-primary flex-1">
          Choose agreement type
        </Text>
      </View>

      <View className="px-lg gap-md">
        <Text className="text-md text-ink-secondary">
          Select the type that best matches your transaction.
        </Text>

        {/* Scenario cards */}
        {SCENARIOS.map((scenario) => (
          <Pressable
            key={scenario.id}
            disabled={mutation.isPending}
            onPress={() => mutation.mutate(scenario.id)}
            className="bg-surface-card rounded-lg p-lg border border-border-subtle flex-row items-center justify-between active:opacity-70"
          >
            <View className="flex-1 gap-xs pr-md">
              <Text className="text-md font-semibold text-ink-primary">
                {scenario.label}
              </Text>
              <Text className="text-sm text-ink-secondary">
                {scenario.shortDescription}
              </Text>
            </View>
            <ChevronRight size={20} color={colors.inkMuted} />
          </Pressable>
        ))}

        {mutation.isError && (
          <Text className="text-sm text-semantic-error text-center">
            {getApiErrorMessage(mutation.error)}
          </Text>
        )}

        {mutation.isPending && (
          <Text className="text-sm text-ink-muted text-center">
            Creating draft…
          </Text>
        )}
      </View>
    </ScrollView>
  );
}
