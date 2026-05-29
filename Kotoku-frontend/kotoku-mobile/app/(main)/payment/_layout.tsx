import { Stack } from "expo-router";

export const unstable_settings = {
  initialRouteName: "checkout",
};

export default function PaymentLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
