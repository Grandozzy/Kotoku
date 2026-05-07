import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { ReeditBanner } from "@/components/agreement/ReeditBanner";
import { StepProgress } from "@/components/agreement/StepProgress";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useDraftPersistence } from "@/hooks/useDraftPersistence";
import { colors } from "@/theme/tokens";

export default function StepsLayout() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const stepIndex = useAgreementStore((s) => s.stepIndex);
  const isReopened = useAgreementStore((s) => s.isReopened);
  const goToStep = useAgreementStore((s) => s.goToStep);
  const reset = useAgreementStore((s) => s.reset);
  useDraftPersistence();

  const handleStepPress = (index: number) => {
    if (!id) return;
    goToStep(index);
    router.replace(`/agreement/${id}/steps/${STEPS[index]}`);
  };

  const handleExit = () => {
    reset();
    router.replace("/(main)/vault");
  };

  const header = () => (
    <View>
      {isReopened && stepIndex === 0 && (
        <View className="flex-row items-center px-lg pt-sm pb-xs bg-surface-card border-b border-border-subtle">
          <Pressable onPress={handleExit} className="p-xs">
            <ChevronLeft size={24} color={colors.inkPrimary} />
          </Pressable>
          <Text className="text-md font-semibold text-ink-primary flex-1 text-center mr-xl">
            Edit agreement
          </Text>
        </View>
      )}
      <StepProgress currentIndex={stepIndex} onStepPress={handleStepPress} />
    </View>
  );

  return (
    <Stack
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen
        name="parties"
        options={{ header, headerShown: true, animation: "none" }}
      />
      <Stack.Screen
        name="details"
        options={{ header, headerShown: true, animation: "none" }}
      />
      <Stack.Screen
        name="evidence"
        options={{ header, headerShown: true, animation: "none" }}
      />
      <Stack.Screen
        name="review"
        options={{ header, headerShown: true, animation: "none" }}
      />
      <Stack.Screen
        name="consent"
        options={{ header, headerShown: true, animation: "none" }}
      />
    </Stack>
  );
}
