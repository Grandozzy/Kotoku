import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { StepProgress } from "@/components/agreement/StepProgress";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useDraftPersistence } from "@/hooks/useDraftPersistence";

export default function StepsLayout() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const stepIndex = useAgreementStore((s) => s.stepIndex);
  const goToStep = useAgreementStore((s) => s.goToStep);
  useDraftPersistence();

  const handleStepPress = (index: number) => {
    if (!id) return;
    goToStep(index);
    router.replace(`/agreement/${id}/steps/${STEPS[index]}`);
  };

  const header = () => <StepProgress currentIndex={stepIndex} onStepPress={handleStepPress} />;

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
