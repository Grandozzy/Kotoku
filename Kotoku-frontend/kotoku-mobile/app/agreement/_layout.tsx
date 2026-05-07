import { Stack, useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/theme/tokens";

function NewAgreementHeader() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View
      className="flex-row items-center px-lg bg-surface-card border-b border-border-subtle"
      style={{ paddingTop: insets.top + 12, paddingBottom: 8 }}
    >
      <Pressable onPress={() => router.back()} className="p-xs">
        <ChevronLeft size={24} color={colors.inkPrimary} />
      </Pressable>
      <Text className="text-md font-semibold text-ink-primary flex-1 text-center mr-xl">
        New Agreement
      </Text>
    </View>
  );
}

export default function AgreementLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen
        name="new"
        options={{ header: () => <NewAgreementHeader />, headerShown: true }}
      />
    </Stack>
  );
}
