import { ChevronLeft } from "lucide-react-native";
import { Linking, Pressable, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/theme/tokens";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

const VERSION = "1.0.0";

export default function AboutScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-xl"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      {/* Header */}
      <View className="flex-row items-center gap-md">
        <Pressable onPress={() => router.back()} className="p-sm -ml-sm active:opacity-70">
          <ChevronLeft size={24} color={colors.inkPrimary} strokeWidth={1.8} />
        </Pressable>
        <Text className="text-2xl font-semibold text-ink-primary">About Kotoku</Text>
      </View>

      {/* Logo block */}
      <View className="items-center gap-md py-lg">
        <KotokuLogo variant="stacked" size={80} color="navy" />
        <Text className="text-sm text-ink-muted">Version {VERSION}</Text>
      </View>

      {/* Mission */}
      <View className="bg-surface-card rounded-2xl p-lg border border-border-subtle gap-sm">
        <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
          Our mission
        </Text>
        <Text className="text-md text-ink-primary leading-relaxed">
          Kotoku exists to make informal agreements trustworthy. We believe a handshake
          should be as enforceable as a contract — with the right evidence behind it.
        </Text>
      </View>

      {/* Legal standing */}
      <View className="bg-ink-primary rounded-2xl p-lg gap-sm">
        <Text className="text-xs font-semibold text-white/50 uppercase tracking-widest">
          Legal standing
        </Text>
        <Text className="text-md font-semibold text-white leading-snug">
          Your sealed record is admissible evidence — not just a screenshot.
        </Text>
        <Text className="text-sm text-white/70 leading-relaxed">
          Kotoku's seal hash, OTP consent records, and immutable vault satisfy
          the admissibility requirements of Ghana's Electronic Transactions Act
          (Act 772), Section 12. Every sealed agreement includes originator
          identification, an integrity hash, and a full audit trail.
        </Text>
      </View>

      {/* Links */}
      <View className="gap-sm">
        <Pressable
          onPress={() => Linking.openURL("https://kotoku.app/legal")}
          className="bg-surface-card rounded-xl border border-border-subtle px-lg py-md flex-row justify-between items-center active:opacity-70"
        >
          <Text className="text-md text-ink-primary">Terms & Privacy Policy</Text>
          <Text className="text-ink-muted">›</Text>
        </Pressable>
        <Pressable
          onPress={() => Linking.openURL("https://kotoku.app")}
          className="bg-surface-card rounded-xl border border-border-subtle px-lg py-md flex-row justify-between items-center active:opacity-70"
        >
          <Text className="text-md text-ink-primary">kotoku.app</Text>
          <Text className="text-ink-muted">›</Text>
        </Pressable>
      </View>

      <Text className="text-xs text-ink-muted text-center">
        © {new Date().getFullYear()} Kotoku. All rights reserved.
      </Text>
    </ScrollView>
  );
}
