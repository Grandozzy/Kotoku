import { Link, Stack } from "expo-router";
import { Text, View } from "react-native";

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: "Not found" }} />
      <View className="flex-1 items-center justify-center bg-surface p-screen">
        <Text className="text-xl font-semibold text-gray-800 mb-4">
          This screen does not exist.
        </Text>
        <Link href="/" className="text-primary underline">
          Go home
        </Link>
      </View>
    </>
  );
}
