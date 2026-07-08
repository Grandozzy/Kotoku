import {
  Bell,
  Check,
  ChevronRight,
  HelpCircle,
  Info,
  LogOut,
  Pencil,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react-native";
import { useState } from "react";
import { KeyboardAvoidingView, Linking, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { BottomSheet, Button, Card, NoticeCard, ScreenLoader } from "@/components/ui";
import { useAuth } from "@/features/auth/useAuth";
import { useMe, useUpdateProfile } from "@/features/auth/otpFlow";
import { usePlan } from "@/features/billing/usePlan";
import { clearSession as clearStoredSession } from "@/lib/secureStore";
import { colors } from "@/theme/tokens";

const ICON_SIZE = 18;
const ICON_STROKE = 1.8;

function EditableRow({
  label,
  value,
  placeholder,
  onSave,
  keyboardType = "default",
  autoCapitalize = "words",
}: {
  label: string;
  value: string;
  placeholder: string;
  onSave: (val: string) => void;
  keyboardType?: "default" | "email-address";
  autoCapitalize?: "none" | "words";
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  const handleSave = () => {
    onSave(draft.trim());
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(value);
    setEditing(false);
  };

  return (
    <View className="gap-xs">
      <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
        {label}
      </Text>
      {editing ? (
        <View className="flex-row items-center gap-sm">
          <TextInput
            value={draft}
            onChangeText={setDraft}
            autoFocus
            keyboardType={keyboardType}
            autoCapitalize={autoCapitalize}
            autoCorrect={false}
            className="flex-1 bg-surface-canvas border border-brand-primary rounded-lg px-md py-sm text-md text-ink-primary"
          />
          <Pressable
            onPress={handleSave}
            className="w-9 h-9 rounded-lg bg-brand-primary items-center justify-center active:opacity-70"
          >
            <Check size={16} color="#ffffff" strokeWidth={2.5} />
          </Pressable>
          <Pressable
            onPress={handleCancel}
            className="w-9 h-9 rounded-lg bg-surface-canvas border border-border-subtle items-center justify-center active:opacity-70"
          >
            <X size={16} color={colors.inkMuted} strokeWidth={2} />
          </Pressable>
        </View>
      ) : (
        <Pressable
          onPress={() => { setDraft(value); setEditing(true); }}
          className="flex-row items-center justify-between active:opacity-70"
        >
          <Text className={`text-md flex-1 ${value ? "text-ink-primary" : "text-ink-muted"}`}>
            {value || placeholder}
          </Text>
          <Pencil size={14} color={colors.inkMuted} strokeWidth={ICON_STROKE} />
        </Pressable>
      )}
    </View>
  );
}

export default function ProfileScreen() {
  const { phone, profileLoading, clearSession } = useAuth();
  const { data: me } = useMe();
  const { data: plan } = usePlan();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const updateMutation = useUpdateProfile();
  const [logoutSheetVisible, setLogoutSheetVisible] = useState(false);

  const fullName: string = me?.full_name ?? "";
  const email: string = me?.email?.endsWith("@kotoku.app") ? "" : (me?.email ?? "");
  const memberSince: string = me?.member_since ?? "";

  // Plan display
  const planName = plan?.plan.name ?? "Personal Basic";
  const usage = plan?.usage;
  const showUsage = plan && plan.flags.is_personal && usage;
  const usagePct = showUsage
    ? Math.min((usage!.sealed_agreements_this_period / plan!.plan.max_agreements_per_month) * 100, 100)
    : 0;
  const upgradeOption = plan?.recommended_upgrades[0];

  const handleSaveName = (val: string) => {
    updateMutation.mutate({ full_name: val });
  };

  const handleSaveEmail = (val: string) => {
    updateMutation.mutate({ email: val });
  };

  const handleLogout = () => {
    setLogoutSheetVisible(true);
  };

  if (profileLoading) return <ScreenLoader rows={3} />;

  const initials = fullName
    ? fullName.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : phone?.slice(-2) ?? "—";

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
      keyboardShouldPersistTaps="handled"
    >
      {/* Header */}
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Profile</Text>
      </View>

      {/* Identity card */}
      <Card elevation="sm">
        <View className="flex-row items-center gap-md mb-lg">
          <View className="w-14 h-14 rounded-full bg-brand-primary items-center justify-center">
            <Text className="text-lg font-bold text-white">{initials}</Text>
          </View>
          <View className="flex-1">
            <Text className="text-md font-semibold text-ink-primary">
              {fullName || "Add your name"}
            </Text>
            <Text className="text-sm text-ink-muted">{phone}</Text>
            {memberSince ? (
              <Text className="text-xs text-ink-muted mt-xs">Member since {memberSince}</Text>
            ) : null}
          </View>
        </View>

        <View className="h-px bg-border-subtle mb-lg" />

        <View className="gap-lg">
          <EditableRow
            label="Full name"
            value={fullName}
            placeholder="Add your full name"
            onSave={handleSaveName}
            autoCapitalize="words"
          />
          <View className="h-px bg-border-subtle" />
          <EditableRow
            label="Email address"
            value={email}
            placeholder="Add your email (optional)"
            onSave={handleSaveEmail}
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        {updateMutation.isError && (
          <NoticeCard
            variant="error"
            title="Could not save changes"
            body="Please try again."
            compact
          />
        )}
      </Card>

      {/* Plan card */}
      <Card elevation="sm" padded={false}>
        <Pressable
          className="px-lg py-md flex-row items-center justify-between border-b border-border-subtle active:opacity-70"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.push((plan?.flags.show_upgrade_recommendation ? "/(main)/plans" : "/(main)/subscription") as any)}
        >
          <View className="flex-row items-center gap-sm">
            <View className="w-8 h-8 rounded-lg bg-brand-primary/10 items-center justify-center">
              <ShieldCheck size={ICON_SIZE} color={colors.brandPrimary} strokeWidth={ICON_STROKE} />
            </View>
            <Text className="text-md font-medium text-ink-primary">{planName}</Text>
          </View>
          <ChevronRight size={16} color={colors.inkMuted} strokeWidth={ICON_STROKE} />
        </Pressable>

        {showUsage && (
          <View className="px-lg py-md gap-xs border-b border-border-subtle">
            <View className="flex-row items-center justify-between">
              <Text className="text-xs text-ink-muted">Seals this month</Text>
              <Text
                className={`text-xs font-semibold ${
                  usage!.is_cap_reached
                    ? "text-semantic-error"
                    : usage!.is_near_cap
                    ? "text-amber-600"
                    : "text-ink-secondary"
                }`}
              >
                {usage!.sealed_agreements_this_period} / {plan!.plan.max_agreements_per_month}
              </Text>
            </View>
            {/* Progress bar */}
            <View className="h-1.5 bg-surface-canvas rounded-full overflow-hidden">
              <View
                className={`h-full rounded-full ${
                  usage!.is_cap_reached
                    ? "bg-semantic-error"
                    : usage!.is_near_cap
                    ? "bg-amber-400"
                    : "bg-brand-primary"
                }`}
                style={{ width: `${usagePct}%` }}
              />
            </View>
          </View>
        )}

        {upgradeOption && plan?.flags.show_upgrade_recommendation && (
          <View className="px-lg py-md flex-row items-center gap-sm bg-amber-50">
            <TrendingUp size={14} color="#d97706" strokeWidth={2} />
            <View className="flex-1">
              <Text className="text-xs text-amber-800 font-medium">
                Upgrade to {upgradeOption.name} — {upgradeOption.price_amount_monthly} GHS/mo
              </Text>
              <Text className="text-xs text-amber-600 mt-xs">
                Up to {upgradeOption.max_agreements_per_month} seals / month
              </Text>
            </View>
          </View>
        )}
      </Card>

      {/* Settings */}
      <Card elevation="sm" padded={false}>
        <Pressable className="px-lg py-md flex-row items-center gap-md border-b border-border-subtle active:bg-surface-canvas">
          <View className="w-8 h-8 rounded-lg bg-surface-canvas items-center justify-center">
            <Bell size={ICON_SIZE} color={colors.inkSecondary} strokeWidth={ICON_STROKE} />
          </View>
          <Text className="flex-1 text-md text-ink-primary">Notifications</Text>
          <ChevronRight size={16} color={colors.inkMuted} strokeWidth={ICON_STROKE} />
        </Pressable>

        <Pressable
          onPress={() => Linking.openURL("https://wa.me/233597110983?text=Hi%2C%20I%20need%20help%20with%20Kotoku")}
          className="px-lg py-md flex-row items-center gap-md border-b border-border-subtle active:bg-surface-canvas"
        >
          <View className="w-8 h-8 rounded-lg bg-surface-canvas items-center justify-center">
            <HelpCircle size={ICON_SIZE} color={colors.inkSecondary} strokeWidth={ICON_STROKE} />
          </View>
          <Text className="flex-1 text-md text-ink-primary">Help & support</Text>
          <ChevronRight size={16} color={colors.inkMuted} strokeWidth={ICON_STROKE} />
        </Pressable>

        <Pressable
          onPress={() => router.push("/(main)/about")}
          className="px-lg py-md flex-row items-center gap-md active:bg-surface-canvas"
        >
          <View className="w-8 h-8 rounded-lg bg-surface-canvas items-center justify-center">
            <Info size={ICON_SIZE} color={colors.inkSecondary} strokeWidth={ICON_STROKE} />
          </View>
          <Text className="flex-1 text-md text-ink-primary">About Kotoku</Text>
          <ChevronRight size={16} color={colors.inkMuted} strokeWidth={ICON_STROKE} />
        </Pressable>
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
      <BottomSheet
        visible={logoutSheetVisible}
        onClose={() => setLogoutSheetVisible(false)}
        title="Log out?"
        body="You will need your phone and PIN again to get back into Kotoku."
        icon={LogOut}
        tone="danger"
        footer={
          <>
            <Button
              title="Stay signed in"
              variant="secondary"
              size="lg"
              fullWidth
              onPress={() => setLogoutSheetVisible(false)}
            />
            <Button
              title="Log out"
              variant="primary"
              size="lg"
              fullWidth
              onPress={async () => {
                setLogoutSheetVisible(false);
                await clearStoredSession();
                clearSession();
              }}
            />
          </>
        }
      />
    </ScrollView>
    </KeyboardAvoidingView>
  );
}
