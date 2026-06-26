import { Tabs } from "expo-router";
import { Home, Lock, Scale, User } from "lucide-react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/theme/tokens";

const SIZE = 22;

export default function MainLayout() {
  const insets = useSafeAreaInsets();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brandPrimary,
        tabBarInactiveTintColor: colors.inkMuted,
        tabBarStyle: {
          backgroundColor: colors.bgCard,
          borderTopColor: colors.borderSubtle,
          height: 60 + insets.bottom,
          paddingBottom: 8 + insets.bottom,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "500",
        },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: "Home",
          tabBarIcon: ({ color, focused }) => (
            <Home size={SIZE} color={color} strokeWidth={focused ? 2.2 : 1.8} />
          ),
        }}
      />
      <Tabs.Screen
        name="vault"
        options={{
          title: "Vault",
          tabBarIcon: ({ color, focused }) => (
            <Lock size={SIZE} color={color} strokeWidth={focused ? 2.2 : 1.8} />
          ),
        }}
      />
      <Tabs.Screen
        name="disputes"
        options={{
          title: "Disputes",
          tabBarIcon: ({ color, focused }) => (
            <Scale size={SIZE} color={color} strokeWidth={focused ? 2.2 : 1.8} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, focused }) => (
            <User size={SIZE} color={color} strokeWidth={focused ? 2.2 : 1.8} />
          ),
        }}
      />
      {/* Hidden from tab bar — navigated to from Profile */}
      <Tabs.Screen
        name="about"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="plans"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="subscription"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="payment"
        options={{ href: null }}
      />
    </Tabs>
  );
}
