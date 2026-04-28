import { useRouter } from "expo-router";
import { Image, Text, View } from "react-native";

import { Button } from "@/components/ui";

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <View className="flex-1 bg-surface-canvas px-lg justify-between py-3xl">
      {/* Logo / hero area */}
      <View className="flex-1 items-center justify-center gap-xl">
        <View className="w-20 h-20 rounded-lg bg-brand-primary items-center justify-center">
          <Text className="text-white text-2xl font-semibold">K</Text>
        </View>
        <View className="items-center gap-sm">
          <Text className="text-2xl font-semibold text-ink-primary">
            Kotoku
          </Text>
          <Text className="text-md text-ink-secondary text-center px-lg">
            A simple way to record and seal agreements between two people.
          </Text>
        </View>
      </View>

      {/* CTA */}
      <View className="gap-sm">
        <Button
          title="Get started"
          variant="primary"
          size="lg"
          fullWidth
          onPress={() => router.push("/(auth)/send-otp")}
        />
        <Text className="text-xs text-ink-muted text-center px-lg">
          By continuing you agree to our Terms of Service and Privacy Policy.
        </Text>
      </View>
    </View>
  );
}
