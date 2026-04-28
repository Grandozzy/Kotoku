import { Tabs } from "expo-router";
import { AlertTriangle, Home, Lock, User } from "lucide-react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/theme/tokens";

const TAB_ICON_SIZE = 22;

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
          tabBarIcon: ({ color }) => (
            <Home size={TAB_ICON_SIZE} color={color} strokeWidth={1.8} />
          ),
        }}
      />
      <Tabs.Screen
        name="vault/index"
        options={{
          title: "Vault",
          tabBarIcon: ({ color }) => (
            <Lock size={TAB_ICON_SIZE} color={color} strokeWidth={1.8} />
          ),
        }}
      />
      {/* Hide the vault detail screen from the tab bar */}
      <Tabs.Screen
        name="vault/[agreementId]"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="disputes"
        options={{
          title: "Disputes",
          tabBarIcon: ({ color }) => (
            <AlertTriangle size={TAB_ICON_SIZE} color={color} strokeWidth={1.8} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color }) => (
            <User size={TAB_ICON_SIZE} color={color} strokeWidth={1.8} />
          ),
        }}
      />
    </Tabs>
  );
}
