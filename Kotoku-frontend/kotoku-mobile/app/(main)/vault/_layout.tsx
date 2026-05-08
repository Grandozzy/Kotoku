import { Stack } from "expo-router";

export const unstable_settings = {
  initialRouteName: "index",
};

export default function VaultLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
