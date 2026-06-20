import { Stack, useLocalSearchParams, usePathname, useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useEffect, useMemo } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { StepProgress } from "@/components/agreement/StepProgress";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useDraftPersistence } from "@/hooks/useDraftPersistence";
import { colors } from "@/theme/tokens";

function ReeditHeader({ onExit }: { onExit: () => void }) {
  const insets = useSafeAreaInsets();

  return (
    <View
      className="flex-row items-center px-lg bg-surface-card"
      style={{ paddingTop: insets.top + 12, paddingBottom: 5 }}
    >
      <Pressable onPress={onExit} className="p-xs">
        <ChevronLeft size={24} color={colors.inkPrimary} />
      </Pressable>
      <Text className="text-md font-semibold text-ink-primary flex-1 text-center mr-xl">
        Edit agreement
      </Text>
    </View>
  );
}

function FormHeader({ onExit }: { onExit: () => void }) {
  const insets = useSafeAreaInsets();

  return (
    <View
      className="flex-row items-center px-lg bg-surface-card"
      style={{ paddingTop: insets.top + 12, paddingBottom: 5 }}
    >
      <Pressable onPress={onExit} className="p-xs">
        <ChevronLeft size={24} color={colors.inkPrimary} />
      </Pressable>
      <Text className="text-md font-semibold text-ink-primary flex-1 text-center mr-xl">
        New Agreement
      </Text>
    </View>
  );
}

export default function StepsLayout() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const stepIndex = useAgreementStore((s) => s.stepIndex);
  const isReopened = useAgreementStore((s) => s.isReopened);
  const consentA = useAgreementStore((s) => s.consentA);
  const consentB = useAgreementStore((s) => s.consentB);
  const goToStep = useAgreementStore((s) => s.goToStep);
  const reset = useAgreementStore((s) => s.reset);
  useDraftPersistence();

  const routeStepIndex = useMemo(() => {
    const currentStep = STEPS.find((step) => pathname.endsWith(`/steps/${step}`));
    return currentStep ? STEPS.indexOf(currentStep) : stepIndex;
  }, [pathname, stepIndex]);

  useEffect(() => {
    if (routeStepIndex !== stepIndex) {
      goToStep(routeStepIndex);
    }
  }, [goToStep, routeStepIndex, stepIndex]);

  const handleStepPress = (index: number) => {
    if (!id) return;
    goToStep(index);
    router.replace(`/agreement/${id}/steps/${STEPS[index]}`);
  };
  const consentStarted =
    routeStepIndex === STEPS.indexOf("consent") &&
    (consentA.otpSent || consentB.otpSent);

  const handleExit = () => {
    reset();
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace("/(main)/home");
    }
  };

  const header = () => (
    <View>
      {isReopened ? (
        <ReeditHeader onExit={handleExit} />
      ) : (
        <FormHeader onExit={handleExit} />
      )}
      <StepProgress
        currentIndex={routeStepIndex}
        onStepPress={consentStarted ? undefined : handleStepPress}
      />
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
