import { useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";

import { SCENARIOS } from "@/constants/scenarios";
import { useCreateDraft } from "@/features/agreements/useAgreementDraft";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { colors } from "@/theme/tokens";

export default function NewAgreementScreen() {
  const router = useRouter();
  const mutation = useCreateDraft();

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-2xl gap-xl"
    >
      {/* Header */}
      <View className="gap-sm">
        <Pressable onPress={() => router.back()}>
          <Text className="text-sm text-brand-primary">← Back</Text>
        </Pressable>
        <Text className="text-2xl font-semibold text-ink-primary">
          Choose agreement type
        </Text>
        <Text className="text-md text-ink-secondary">
          Select the type that best matches your transaction.
        </Text>
      </View>

      {/* Scenario cards */}
      <View className="gap-md">
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
      </View>

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
    </ScrollView>
  );
}
