import { useRouter } from "expo-router";
import { CheckCircle } from "lucide-react-native";
import { Text, View } from "react-native";

import { Button } from "@/components/ui";
import { colors } from "@/theme/tokens";

export default function SealedScreen() {
  const router = useRouter();

  return (
    <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
      <CheckCircle size={72} color={colors.success} strokeWidth={1.5} />

      <View className="items-center gap-sm">
        <Text className="text-2xl font-semibold text-ink-primary text-center">
          Agreement sealed
        </Text>
        <Text className="text-md text-ink-secondary text-center">
          Both parties have confirmed. The agreement is now sealed and saved to
          your vault.
        </Text>
      </View>

      <View className="w-full gap-md">
        <Button
          title="View in vault"
          variant="primary"
          size="lg"
          fullWidth
          onPress={() => router.replace("/(main)/vault")}
        />
        <Button
          title="Start another agreement"
          variant="secondary"
          size="lg"
          fullWidth
          onPress={() => router.replace("/agreement/new")}
        />
      </View>
    </View>
  );
}
