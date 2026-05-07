import { Text, View, Pressable } from "react-native";
import { ScrollView } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Card } from "@/components/ui";
import { useAuth } from "@/features/auth/useAuth";
import { clearSession as clearStoredSession } from "@/lib/secureStore";

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
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Profile</Text>
      </View>

      {/* Account info */}
      <Card elevation="sm">
        <Text className="text-xs text-ink-muted mb-xs">Phone number</Text>
        <Text className="text-md font-medium text-ink-primary">
          {phone || "—"}
        </Text>
      </Card>

      {/* Settings rows — expanded in later phase */}
      <Card elevation="sm" padded={false}>
        {[
          "Storage plan",
          "Language",
          "Privacy settings",
          "Help & support",
          "About Kotoku",
        ].map((item, i, arr) => (
          <Pressable
            key={item}
            className={`px-lg py-md flex-row justify-between items-center ${
              i < arr.length - 1 ? "border-b border-border-subtle" : ""
            }`}
          >
            <Text className="text-md text-ink-primary">{item}</Text>
            <Text className="text-ink-muted">›</Text>
          </Pressable>
        ))}
      </Card>

      <Button
        title="Log out"
        variant="secondary"
        size="lg"
        fullWidth
        onPress={handleLogout}
      />
    </ScrollView>
  );
}
