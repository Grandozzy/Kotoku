import { useRouter } from "expo-router";
import { CheckCircle, Clock, RefreshCw } from "lucide-react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Button, OTPInput } from "@/components/ui";
import { useSessionStore } from "@/store/sessionStore";
import { getApiErrorMessage } from "@/lib/errorHandler";
import {
  useConfirmReopen,
  useRequestReopen,
  useResendReopenOtp,
} from "@/features/vault/useReopen";
import { colors } from "@/theme/tokens";
import type { AgreementStatus } from "@/types/vault";

interface ReopenSectionProps {
  agreementId: number;
  agreementStatus: AgreementStatus;
  createdByPhone: string;
}

export function ReopenSection({
  agreementId,
  agreementStatus,
  createdByPhone,
}: ReopenSectionProps) {
  const phone = useSessionStore((s) => s.phone);
  const isCreator = phone === createdByPhone;

  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [confirmedByMe, setConfirmedByMe] = useState(false);
  const [reopened, setReopened] = useState(false);

  const requestReopen = useRequestReopen(agreementId);
  const resendOtp = useResendReopenOtp(agreementId);
  const confirmReopen = useConfirmReopen(agreementId);

  if (
    agreementStatus === "active" ||
    agreementStatus === "draft" ||
    agreementStatus === "pending_consent"
  ) {
    return null;
  }

  const error =
    requestReopen.isError
      ? getApiErrorMessage(requestReopen.error)
      : confirmReopen.isError
        ? getApiErrorMessage(confirmReopen.error)
        : null;

  if (agreementStatus === "sealed") {
    if (!isCreator) return null;
    return (
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Reopen Agreement
        </Text>
        <Text className="text-sm text-ink-secondary">
          Request to reopen this agreement. Both parties must confirm with a
          one-time code before it becomes editable again.
        </Text>
        <Button
          title="Request Reopen"
          variant="secondary"
          size="md"
          fullWidth
          loading={requestReopen.isPending}
          onPress={() => {
            requestReopen.mutate(undefined, {
              onSuccess: () => setOtpSent(true),
            });
          }}
        />
        {error && (
          <Text className="text-xs text-semantic-error text-center">{error}</Text>
        )}
      </View>
    );
  }

  if (agreementStatus === "reopen_requested") {
    if (reopened) {
      return (
        <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-sm">
          <View className="flex-row items-center gap-sm">
            <CheckCircle size={18} color={colors.success} />
            <Text className="text-sm font-medium text-emerald-700">
              Agreement reopened!
            </Text>
          </View>
          <Text className="text-sm text-ink-muted">
            Both parties confirmed. The agreement is now editable.
          </Text>
        </View>
      );
    }

    return (
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Confirm Reopen
        </Text>
        <Text className="text-sm text-ink-secondary">
          Enter the code sent to {phone ?? "your phone"} to confirm.
        </Text>

        {confirmedByMe ? (
          <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-sm">
            <View className="flex-row items-center gap-sm">
              <CheckCircle size={18} color={colors.success} />
              <Text className="text-sm font-medium text-emerald-700">
                You&apos;ve confirmed
              </Text>
            </View>
            <View className="flex-row items-center gap-sm">
              <Clock size={16} color={colors.inkMuted} />
              <Text className="text-sm text-ink-muted">
                Waiting for the other party to confirm…
              </Text>
            </View>
          </View>
        ) : (
          <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-md">
            <OTPInput
              value={otpCode}
              onChange={(v) => {
                setOtpCode(v);
                if (confirmReopen.isError) confirmReopen.reset();
              }}
              error={error ?? undefined}
              disabled={confirmReopen.isPending}
            />
            <Button
              title="Confirm Reopen"
              variant="primary"
              size="md"
              fullWidth
              disabled={otpCode.length < 8}
              loading={confirmReopen.isPending}
              onPress={() => {
                if (!phone) return;
                confirmReopen.mutate(
                  { phone, otpCode },
                  {
                    onSuccess: (result) => {
                      if (result.agreement_status === "active") {
                        setReopened(true);
                      } else if (result.granted) {
                        setConfirmedByMe(true);
                      }
                    },
                  },
                );
              }}
            />
            <Pressable
              onPress={() => resendOtp.mutate()}
              disabled={resendOtp.isPending}
              className="flex-row items-center justify-center gap-xs"
            >
              <RefreshCw
                size={14}
                color={resendOtp.isPending ? colors.inkMuted : colors.brandPrimary}
              />
              <Text
                className={`text-sm ${resendOtp.isPending ? "text-ink-muted" : "text-brand-primary"}`}
              >
                {resendOtp.isPending ? "Sending…" : "Resend code"}
              </Text>
            </Pressable>
          </View>
        )}
      </View>
    );
  }

  return null;
}
