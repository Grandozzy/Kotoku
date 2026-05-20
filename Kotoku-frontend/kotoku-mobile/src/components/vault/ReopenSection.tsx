import { useQuery } from "@tanstack/react-query";
import { CheckCircle, Clock, RefreshCw } from "lucide-react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Button, OTPInput } from "@/components/ui";
import { getAgreement } from "@/api/agreements";
import { getApiErrorMessage } from "@/lib/errorHandler";
import {
  useConfirmReopen,
  useRequestReopen,
  useResendReopenOtp,
} from "@/features/vault/useReopen";
import { useSessionStore } from "@/store/sessionStore";
import { colors } from "@/theme/tokens";
import type { AgreementStatus, PartySummary } from "@/types/vault";

interface ReopenSectionProps {
  agreementId: number;
  agreementStatus: AgreementStatus;
  parties: PartySummary[];
}

export function ReopenSection({
  agreementId,
  agreementStatus,
  parties,
}: ReopenSectionProps) {
  const [otpCodeA, setOtpCodeA] = useState("");
  const [otpCodeB, setOtpCodeB] = useState("");
  const [confirmedA, setConfirmedA] = useState(false);
  const [confirmedB, setConfirmedB] = useState(false);
  const [reopened, setReopened] = useState(false);
  const authenticatedPhone = useSessionStore((s) => s.phone);

  const requestReopen = useRequestReopen(agreementId);
  const resendOtp = useResendReopenOtp(agreementId);
  const confirmReopen = useConfirmReopen(agreementId);

  const { data: agreementParties } = useQuery({
    queryKey: ["agreement", agreementId, "parties"],
    queryFn: async () => {
      const agreement = await getAgreement(agreementId);
      return agreement.parties;
    },
    enabled: agreementStatus === "reopen_requested",
  });

  const vaultParties = parties ?? [];
  const effectiveParties = vaultParties.length >= 2 ? vaultParties : (agreementParties ?? []);
  const partyA = effectiveParties[0];
  const partyB = effectiveParties[1];
  const currentParty =
    authenticatedPhone && partyA?.phone === authenticatedPhone
      ? "A"
      : authenticatedPhone && partyB?.phone === authenticatedPhone
        ? "B"
        : null;

  const error: string | undefined =
    requestReopen.isError
      ? getApiErrorMessage(requestReopen.error)
      : confirmReopen.isError
        ? getApiErrorMessage(confirmReopen.error)
        : undefined;

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

  if (
    agreementStatus === "active" ||
    agreementStatus === "draft" ||
    agreementStatus === "pending_consent"
  ) {
    return null;
  }

  if (agreementStatus === "sealed") {
    return (
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Reopen Agreement
        </Text>
        <Text className="text-sm text-ink-secondary">
          Request to reopen this agreement. Both parties must confirm with a
          one-time code before it becomes editable again.
        </Text>
        <View className="bg-amber-50 border border-amber-100 rounded-xl p-md gap-xs">
          <Text className="text-xs font-semibold text-amber-900">
            Confirm reopen from the matching phone account.
          </Text>
          <Text className="text-xs text-amber-800 leading-relaxed">
            The counterparty must sign in on their own device or invite link and
            enter only the OTP sent to their phone.
          </Text>
        </View>
        <Button
          title="Request Reopen"
          variant="secondary"
          size="md"
          fullWidth
          loading={requestReopen.isPending}
          onPress={() => requestReopen.mutate()}
        />
        {error && (
          <Text className="text-xs text-semantic-error text-center">{error}</Text>
        )}
      </View>
    );
  }

  if (agreementStatus === "reopen_requested") {
    const allConfirmed = confirmedA && confirmedB;

    return (
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Confirm Reopen
        </Text>
        <Text className="text-sm text-ink-secondary">
          Both parties must enter the code sent to their phone while signed in as
          that same phone/account.
        </Text>

        {!currentParty && (
          <View className="bg-amber-50 border border-amber-100 rounded-xl p-md">
            <Text className="text-xs text-amber-800 leading-relaxed">
              This signed-in phone is not one of the parties waiting to reopen.
              Sign in with the phone that received the reopen OTP.
            </Text>
          </View>
        )}

        {partyA && currentParty === "A" && (
          <ReopenPartyBlock
            role={partyA.role}
            phone={partyA.phone}
            displayName={partyA.displayName}
            confirmed={confirmedA}
            code={otpCodeA}
            onCodeChange={(v) => {
              setOtpCodeA(v);
              if (confirmReopen.isError) confirmReopen.reset();
            }}
            onConfirm={() => {
              confirmReopen.mutate(
                { phone: partyA.phone, otpCode: otpCodeA },
                {
                  onSuccess: (result) => {
                    setConfirmedA(true);
                    if (result.agreement_status === "active") setReopened(true);
                  },
                },
              );
            }}
            loading={confirmReopen.isPending}
            error={error}
            disabled={confirmedA}
          />
        )}

        {partyB && currentParty === "B" && (
          <ReopenPartyBlock
            role={partyB.role}
            phone={partyB.phone}
            displayName={partyB.displayName}
            confirmed={confirmedB}
            code={otpCodeB}
            onCodeChange={(v) => {
              setOtpCodeB(v);
              if (confirmReopen.isError) confirmReopen.reset();
            }}
            onConfirm={() => {
              confirmReopen.mutate(
                { phone: partyB.phone, otpCode: otpCodeB },
                {
                  onSuccess: (result) => {
                    setConfirmedB(true);
                    if (result.agreement_status === "active") setReopened(true);
                  },
                },
              );
            }}
            loading={confirmReopen.isPending}
            error={error}
            disabled={confirmedB}
          />
        )}

        {currentParty && !allConfirmed && (
          <View className="bg-blue-50 border border-blue-100 rounded-xl p-md">
            <Text className="text-xs text-blue-800 leading-relaxed">
              Only your reopen OTP can be confirmed from this account. The other
              party must sign in with their own phone and confirm separately.
            </Text>
          </View>
        )}

        {!allConfirmed && (
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
              {resendOtp.isPending ? "Sending…" : "Resend codes"}
            </Text>
          </Pressable>
        )}

        {error && (
          <Text className="text-xs text-semantic-error text-center">{error}</Text>
        )}
      </View>
    );
  }

  return null;
}

interface ReopenPartyBlockProps {
  role: string;
  phone: string;
  displayName: string;
  confirmed: boolean;
  code: string;
  onCodeChange: (v: string) => void;
  onConfirm: () => void;
  loading: boolean;
  error?: string;
  disabled: boolean;
}

function ReopenPartyBlock({
  role,
  phone,
  displayName,
  confirmed,
  code,
  onCodeChange,
  onConfirm,
  loading,
  error,
  disabled,
}: ReopenPartyBlockProps) {
  return (
    <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-md">
      <View className="flex-row items-center justify-between">
        <View>
          <Text className="text-md font-semibold text-ink-primary">
            {displayName}
          </Text>
          <Text className="text-xs text-ink-muted">{role} - {phone}</Text>
        </View>
        {confirmed ? (
          <View className="flex-row items-center gap-xs">
            <CheckCircle size={16} color={colors.success} />
            <Text className="text-sm font-medium text-emerald-600">Confirmed</Text>
          </View>
        ) : (
          <View className="flex-row items-center gap-xs">
            <Clock size={16} color={colors.inkMuted} />
            <Text className="text-sm text-ink-muted">Pending</Text>
          </View>
        )}
      </View>
      {!confirmed && (
        <>
          <OTPInput
            value={code}
            onChange={onCodeChange}
            error={error}
            disabled={disabled || loading}
          />
          <Button
            title={`Confirm ${displayName}`}
            variant="primary"
            size="md"
            fullWidth
            disabled={code.length < 8 || disabled}
            loading={loading}
            onPress={onConfirm}
          />
        </>
      )}
    </View>
  );
}
