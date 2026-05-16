import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { StepProgress } from "@/components/agreement/StepProgress";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useDraftSession } from "@/hooks/useDraftSession";
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
  const router = useRouter();
  const stepIndex = useAgreementStore((s) => s.stepIndex);
  const isReopened = useAgreementStore((s) => s.isReopened);
  const goToStep = useAgreementStore((s) => s.goToStep);
  const reset = useAgreementStore((s) => s.reset);
  const { abandon } = useDraftSession();

  const handleStepPress = (index: number) => {
    if (!id) return;
    goToStep(index);
    router.replace(`/agreement/${id}/steps/${STEPS[index]}`);
  };

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
