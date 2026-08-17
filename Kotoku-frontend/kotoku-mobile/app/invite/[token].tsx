import { useLocalSearchParams, useRouter } from "expo-router";
import { AlertCircle, Clock, UserCheck } from "lucide-react-native";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { claimIdentityInvite, getIdentityInviteDetail, type IdentityInviteDetail } from "@/api/agreements";
import { Button, NoticeCard, ScreenLoader } from "@/components/ui";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { useSessionStore } from "@/store/sessionStore";

export default function InviteScreen() {
  const router = useRouter();
  const { token } = useLocalSearchParams<{ token: string }>();
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);

  const [detail, setDetail] = useState<IdentityInviteDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [claiming, setClaiming] = useState(false);
  const [claimError, setClaimError] = useState<string | null>(null);

  // Fetch invite metadata (no auth required) so we can show a preview.
  useEffect(() => {
    if (!token) return;
    getIdentityInviteDetail(token)
      .then(setDetail)
      .catch((err) => {
        setLoadError(getApiErrorMessage(err, "This invite link is not valid or has expired."));
      });
  }, [token]);

  const handleContinue = async () => {
    if (!isAuthenticated) {
      // Save token to navigate back after auth.
      router.push({
        pathname: "/(auth)/welcome",
        params: { pendingInviteToken: token },
      } as never);
      return;
    }

    if (!token) return;
    setClaiming(true);
    setClaimError(null);
    try {
      const { agreement_id, role } = await claimIdentityInvite(token);
      router.replace({
        pathname: "/agreement/[id]/steps/identity-invite",
        params: { id: String(agreement_id), role },
      } as never);
    } catch (err) {
      const msg = getApiErrorMessage(err, "Could not start the identity check.");
      if (msg.toLowerCase().includes("phone number")) {
        setClaimError(
          "This invite was sent to a different phone number. Log in with the number that received the SMS.",
        );
      } else {
        setClaimError(msg);
      }
    } finally {
      setClaiming(false);
    }
  };

  if (!token) {
    return (
      <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
        <AlertCircle size={44} color="#dc2626" strokeWidth={1.5} />
        <Text className="text-xl font-semibold text-ink-primary text-center">Invalid link</Text>
        <Text className="text-sm text-ink-secondary text-center">
          This invite link is missing required information.
        </Text>
      </View>
    );
  }

  if (!detail && !loadError) {
    return <ScreenLoader />;
  }

  if (loadError) {
    return (
      <View className="flex-1 bg-surface-canvas px-lg items-center justify-center gap-xl">
        <View className="w-20 h-20 rounded-full bg-red-50 items-center justify-center">
          <AlertCircle size={36} color="#dc2626" strokeWidth={1.6} />
        </View>
        <View className="items-center gap-sm">
          <Text className="text-2xl font-semibold text-ink-primary text-center">
            Invite unavailable
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed">
            {loadError}
          </Text>
        </View>
        <Button
          title="Go home"
          variant="secondary"
          size="lg"
          fullWidth
          onPress={() => router.replace("/(main)/home" as never)}
        />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-surface-canvas px-lg justify-center gap-xl">
      <View className="w-20 h-20 rounded-full bg-blue-50 items-center justify-center self-center">
        <UserCheck size={40} color="#2563EB" strokeWidth={1.5} />
      </View>

      <View className="items-center gap-sm">
        <Text className="text-2xl font-semibold text-ink-primary text-center">
          Identity verification
        </Text>
        <Text className="text-md text-ink-secondary text-center leading-relaxed">
          You have been invited to verify your identity for
        </Text>
        <Text className="text-lg font-semibold text-ink-primary text-center">
          {detail!.agreement_title}
        </Text>
        <Text className="text-sm text-ink-muted text-center">
          as {detail!.role} ({detail!.party_name})
        </Text>
      </View>

      <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
        <View className="flex-row items-center gap-md">
          <Clock size={18} color="#6b7280" strokeWidth={1.8} />
          <Text className="text-sm text-ink-secondary flex-1">
            You will upload your Ghana Card (front and back) and complete a face liveness check. This takes around 2 minutes.
          </Text>
        </View>
      </View>

      {!isAuthenticated && (
        <NoticeCard
          variant="info"
          title="Log in first"
          body="You need to log in with the phone number that received this invite before you can proceed."
          compact
        />
      )}

      {claimError && (
        <NoticeCard variant="error" title="Could not start" body={claimError} compact />
      )}

      <Button
        title={
          claiming
            ? "Starting…"
            : isAuthenticated
              ? "Start identity verification"
              : "Log in to continue"
        }
        variant="primary"
        size="lg"
        fullWidth
        loading={claiming}
        onPress={() => void handleContinue()}
      />
    </View>
  );
}
