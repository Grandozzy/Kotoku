import { Stack } from "expo-router";

import { StepProgress } from "@/components/agreement/StepProgress";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { useDraftPersistence } from "@/hooks/useDraftPersistence";

export default function StepsLayout() {
  const stepIndex = useAgreementStore((s) => s.stepIndex);
  useDraftPersistence();

  return (
    <Stack
      screenOptions={{ headerShown: false }}
      // StepProgress sits above all step screens
    >
      <Stack.Screen
        name="parties"
        options={{
          header: () => <StepProgress currentIndex={stepIndex} />,
          headerShown: true,
        }}
      />
      <Stack.Screen
        name="details"
        options={{
          header: () => <StepProgress currentIndex={stepIndex} />,
          headerShown: true,
        }}
      />
      <Stack.Screen
        name="evidence"
        options={{
          header: () => <StepProgress currentIndex={stepIndex} />,
          headerShown: true,
        }}
      />
      <Stack.Screen
        name="review"
        options={{
          header: () => <StepProgress currentIndex={stepIndex} />,
          headerShown: true,
        }}
      />
      <Stack.Screen
        name="consent"
        options={{
          header: () => <StepProgress currentIndex={stepIndex} />,
          headerShown: true,
        }}
      />
    </Stack>
  );
}
