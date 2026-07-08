import { useRouter } from "expo-router";
import {
  Briefcase,
  Building2,
  Camera,
  Car,
  MessageSquare,
  ShieldCheck,
  Users,
} from "lucide-react-native";
import { ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
import { colors } from "@/theme/tokens";

const STEPS = [
  {
    Icon: Camera,
    title: "Capture",
    body: "Photograph the asset, upload IDs, and record the agreed terms. Everything is timestamped on arrival.",
  },
  {
    Icon: MessageSquare,
    title: "Confirm",
    body: "Both parties receive an SMS OTP. No one can seal alone, and each confirmation is linked to a verified phone number.",
  },
  {
    Icon: ShieldCheck,
    title: "Seal",
    body: "A tamper-evident vault entry is created. It is hashed, timestamped, and retrievable any time.",
  },
];

const USE_CASES = [
  { Icon: Car,       label: "Vehicle sale" },
  { Icon: Building2, label: "Room rental" },
  { Icon: Users,     label: "Informal deals" },
  { Icon: Briefcase, label: "Small business" },
];

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-3xl"
      showsVerticalScrollIndicator={false}
    >
      {/* Hero */}
      <View className="items-center gap-md pt-3xl pb-xl">
        <KotokuLogo variant="stacked" size={80} color="navy" />
        <View className="items-center gap-xs">
          <Text className="text-xs font-semibold text-brand-primary tracking-widest uppercase">
            Agreement Evidence Platform
          </Text>
          <Text className="text-3xl font-bold text-ink-primary text-center leading-tight">
            Don't take their word for it.
          </Text>
          <Text className="text-3xl font-bold text-brand-primary text-center leading-tight">
            Take evidence for it.
          </Text>
        </View>
        <Text className="text-md text-ink-secondary text-center leading-relaxed px-md mt-xs">
          Capture photos, agree on terms, and seal the deal with bilateral SMS
          confirmation and a tamper-proof vault. In under five minutes.
        </Text>
        <View className="flex-row flex-wrap justify-center gap-sm pt-xs">
          <View className="rounded-full bg-brand-primary/10 px-md py-xs">
            <Text className="text-xs font-semibold text-brand-primary">SMS consent</Text>
          </View>
          <View className="rounded-full bg-emerald-50 px-md py-xs">
            <Text className="text-xs font-semibold text-emerald-700">Tamper-proof vault</Text>
          </View>
          <View className="rounded-full bg-amber-50 px-md py-xs">
            <Text className="text-xs font-semibold text-amber-700">Court-ready record</Text>
          </View>
        </View>
      </View>

      {/* How it works */}
      <View className="gap-sm mb-xl">
        {STEPS.map(({ Icon, title, body }, index) => (
          <View
            key={title}
            className="bg-surface-card rounded-2xl p-lg flex-row gap-md items-start border border-border-subtle"
          >
            <View className="items-center gap-xs">
              <View className="w-10 h-10 rounded-xl bg-brand-primary/10 items-center justify-center">
                <Icon size={20} color={colors.brandPrimary} strokeWidth={1.8} />
              </View>
              <Text className="text-[10px] font-semibold tracking-widest text-brand-primary/70">
                0{index + 1}
              </Text>
            </View>
            <View className="flex-1 gap-xs">
              <Text className="text-md font-semibold text-ink-primary">{title}</Text>
              <Text className="text-sm text-ink-secondary leading-relaxed">{body}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Use cases — icon pill row */}
      <View className="flex-row flex-wrap gap-sm mb-xl justify-center">
        {USE_CASES.map(({ Icon, label }) => (
          <View
            key={label}
            className="flex-row items-center gap-xs bg-surface-card border border-border-subtle rounded-full px-md py-sm"
          >
            <Icon size={14} color={colors.inkSecondary} strokeWidth={1.8} />
            <Text className="text-xs font-medium text-ink-secondary">{label}</Text>
          </View>
        ))}
      </View>

      {/* Legal trust bar */}
      <View className="bg-ink-primary rounded-3xl px-lg py-lg gap-sm mb-xl flex-row items-start">
        <View className="w-9 h-9 rounded-lg bg-white/10 items-center justify-center mt-xs">
          <ShieldCheck size={18} color="#ffffff" strokeWidth={1.8} />
        </View>
        <View className="flex-1 gap-xs">
          <Text className="text-xs uppercase tracking-widest text-white/50 font-semibold">
            Legal standing
          </Text>
          <Text className="text-sm font-semibold text-white leading-snug">
            Your sealed record is admissible evidence and not just a screenshot.
          </Text>
          <Text className="text-xs text-white/60 leading-relaxed">
            Recognised under Ghana's Electronic Transactions Act (Act 772), Section 12.
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
    </ScrollView>
  );
}
