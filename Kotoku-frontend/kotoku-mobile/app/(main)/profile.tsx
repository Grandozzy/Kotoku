import {
  Bell,
  ChevronRight,
  Globe,
  HelpCircle,
  Info,
  Lock,
  LogOut,
} from "lucide-react-native";
import { ScrollView, Text, View, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Card } from "@/components/ui";
import { useAuth } from "@/features/auth/useAuth";
import { clearSession as clearStoredSession } from "@/lib/secureStore";
import { colors } from "@/theme/tokens";

const ICON_SIZE = 18;
const ICON_STROKE = 1.8;

const SETTINGS = [
  { icon: Bell,       label: "Notifications",   value: null },
  { icon: Globe,      label: "Language",         value: "English" },
  { icon: Lock,       label: "Privacy settings", value: null },
  { icon: HelpCircle, label: "Help & support",   value: null },
  { icon: Info,       label: "About Kotoku",     value: null },
];

export default function ProfileScreen() {
  const { phone, clearSession } = useAuth();
  const insets = useSafeAreaInsets();

  const handleLogout = async () => {
    await clearStoredSession();
    clearSession();
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      {/* Header */}
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Profile</Text>
      </View>

      {/* Account card */}
      <Card elevation="sm">
        <View className="flex-row items-center gap-md">
          <View className="w-12 h-12 rounded-full bg-brand-primary/10 items-center justify-center">
            <Text className="text-lg font-bold text-brand-primary">
              {phone ? phone.slice(-2) : "—"}
            </Text>
          </View>
          <View>
            <Text className="text-xs text-ink-muted">Phone number</Text>
            <Text className="text-md font-semibold text-ink-primary mt-0.5">
              {phone || "—"}
            </Text>
          </View>
        </View>
      </Card>

      {/* Settings list */}
      <Card elevation="sm" padded={false}>
        {SETTINGS.map(({ icon: Icon, label, value }, i) => (
          <Pressable
            key={label}
            className={`px-lg py-md flex-row items-center gap-md active:bg-surface-canvas ${
              i < SETTINGS.length - 1 ? "border-b border-border-subtle" : ""
            }`}
          >
            <View className="w-8 h-8 rounded-lg bg-surface-canvas items-center justify-center">
              <Icon size={ICON_SIZE} color={colors.inkSecondary} strokeWidth={ICON_STROKE} />
            </View>
            <Text className="flex-1 text-md text-ink-primary">{label}</Text>
            {value && (
              <Text className="text-sm text-ink-muted mr-xs">{value}</Text>
            )}
            <ChevronRight size={16} color={colors.inkMuted} strokeWidth={ICON_STROKE} />
          </Pressable>
        ))}
      </Card>

      {/* Log out */}
      <Pressable
        onPress={handleLogout}
        className="flex-row items-center gap-md px-lg py-md bg-surface-card rounded-xl border border-border-subtle active:opacity-70"
      >
        <View className="w-8 h-8 rounded-lg bg-semantic-error/10 items-center justify-center">
          <LogOut size={ICON_SIZE} color={colors.error} strokeWidth={ICON_STROKE} />
        </View>
        <Text className="text-md font-medium text-semantic-error">Log out</Text>
      </Pressable>
    </ScrollView>
  );
}
