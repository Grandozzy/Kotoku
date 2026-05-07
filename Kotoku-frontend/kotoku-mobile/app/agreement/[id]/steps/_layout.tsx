import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { View } from "react-native";

import { ReeditBanner } from "@/components/agreement/ReeditBanner";
import { StepProgress } from "@/components/agreement/StepProgress";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useDraftPersistence } from "@/hooks/useDraftPersistence";

export default function StepsLayout() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const stepIndex = useAgreementStore((s) => s.stepIndex);
  const isReopened = useAgreementStore((s) => s.isReopened);
  const goToStep = useAgreementStore((s) => s.goToStep);
  useDraftPersistence();

  const handleStepPress = (index: number) => {
    if (!id) return;
    goToStep(index);
    router.replace(`/agreement/${id}/steps/${STEPS[index]}`);
  };

  const header = () => (
    <View>
      {isReopened && <ReeditBanner />}
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
