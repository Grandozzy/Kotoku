import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircle, Clock } from "lucide-react-native";
import { useState } from "react";
import { ScrollView, Text, View } from "react-native";

import { Button, OTPInput } from "@/components/ui";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import {
  useConfirmOtp,
  useRequestOtp,
  getApiErrorMessage,
} from "@/features/consent/useConsentFlow";
import { useSealAgreement } from "@/features/agreements/useAgreementDraft";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { colors } from "@/theme/tokens";

export default function ConsentStep() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const agreementId = Number(id);

  const { scenarioId, consentA, consentB, prevStep, stepIndex } = useAgreementStore();
  const template = useTemplate(scenarioId);
  const [roleA, roleB] = template?.partyRoles ?? ["Party A", "Party B"];

  const [codeA, setCodeA] = useState("");
  const [codeB, setCodeB] = useState("");

  const requestOtp = useRequestOtp(agreementId);
  const confirmOtp = useConfirmOtp(agreementId);
  const sealMutation = useSealAgreement(agreementId);

  const bothConfirmed = consentA.confirmed && consentB.confirmed;
  const otpsSent = consentA.otpSent && consentB.otpSent;

  // TODO: replace hardcoded partyId placeholders with real IDs from the agreement
  // once the parties API is wired. For now these are sentinel values.
  const PARTY_A_ID = 1;
  const PARTY_B_ID = 2;

  const handleRequestCodes = () => {
    requestOtp.mutate({ party: "A", partyId: PARTY_A_ID });
    requestOtp.mutate({ party: "B", partyId: PARTY_B_ID });
  };

  const handleConfirmA = () => {
    if (!consentA.consentRecordId) return;
    confirmOtp.mutate({
      party: "A",
      consentRecordId: consentA.consentRecordId,
      otpCode: codeA,
    });
  };

  const handleConfirmB = () => {
    if (!consentB.consentRecordId) return;
    confirmOtp.mutate({
      party: "B",
      consentRecordId: consentB.consentRecordId,
      otpCode: codeB,
    });
  };

  const confirmError =
    confirmOtp.isError ? getApiErrorMessage(confirmOtp.error) : null;

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
      contentContainerStyle={{ paddingBottom: 60 }}
    >
      <View className="gap-sm">
        <Text className="text-xl font-semibold text-ink-primary">
          Confirm consent
        </Text>
        <Text className="text-md text-ink-secondary">
          Both parties must confirm with a one-time code before the agreement
          can be sealed.
        </Text>
      </View>

      {/* Request codes button */}
      {!otpsSent && (
        <Button
          title="Request consent codes"
          variant="primary"
          size="lg"
          fullWidth
          loading={requestOtp.isPending}
          onPress={handleRequestCodes}
        />
      )}

      {requestOtp.isError && (
        <Text className="text-sm text-semantic-error text-center">
          {getApiErrorMessage(requestOtp.error)}
        </Text>
      )}

      {/* Party A OTP */}
      {otpsSent && (
        <ConsentPartyBlock
          role={roleA}
          confirmed={consentA.confirmed}
          code={codeA}
          onCodeChange={(v) => {
            setCodeA(v);
            if (confirmOtp.isError) confirmOtp.reset();
          }}
          onConfirm={handleConfirmA}
          loading={confirmOtp.isPending}
          error={confirmError ?? undefined}
          disabled={consentA.confirmed}
        />
      )}

      {/* Party B OTP */}
      {otpsSent && (
        <ConsentPartyBlock
          role={roleB}
          confirmed={consentB.confirmed}
          code={codeB}
          onCodeChange={(v) => {
            setCodeB(v);
            if (confirmOtp.isError) confirmOtp.reset();
          }}
          onConfirm={handleConfirmB}
          loading={confirmOtp.isPending}
          error={confirmError ?? undefined}
          disabled={consentB.confirmed}
        />
      )}

      {/* Seal */}
      {bothConfirmed && (
        <View className="gap-md">
          <View className="flex-row items-center justify-center gap-sm bg-emerald-50 rounded-lg p-md">
            <CheckCircle size={18} color={colors.success} />
            <Text className="text-sm font-medium text-emerald-700">
              Both parties have confirmed
            </Text>
          </View>
          <View className="flex-row gap-sm">
            {stepIndex > 0 && (
              <View style={{ flex: 1 }}>
                <Button
                  title="Back"
                  variant="secondary"
                  size="lg"
                  onPress={() => {
                    prevStep();
                    router.replace(`/agreement/${id}/steps/${STEPS[stepIndex - 1]}`);
                  }}
                />
              </View>
            )}
            <View style={{ flex: 2 }}>
              <Button
                title="Seal agreement"
                variant="primary"
                size="lg"
                loading={sealMutation.isPending}
                onPress={() => sealMutation.mutate()}
              />
            </View>
          </View>
          {sealMutation.isError && (
            <Text className="text-sm text-semantic-error text-center">
              {getApiErrorMessage(sealMutation.error)}
            </Text>
          )}
        </View>
      )}

      {!bothConfirmed && stepIndex > 0 && (
        <Button
          title="Back"
          variant="secondary"
          size="lg"
          fullWidth
          onPress={() => {
            prevStep();
            router.replace(`/agreement/${id}/steps/${STEPS[stepIndex - 1]}`);
          }}
        />
      )}
    </ScrollView>
  );
}

// ---------- Sub-component ----------

interface ConsentPartyBlockProps {
  role: string;
  confirmed: boolean;
  code: string;
  onCodeChange: (v: string) => void;
  onConfirm: () => void;
  loading: boolean;
  error?: string;
  disabled: boolean;
}

function ConsentPartyBlock({
  role,
  confirmed,
  code,
  onCodeChange,
  onConfirm,
  loading,
  error,
  disabled,
}: ConsentPartyBlockProps) {
  return (
    <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-md">
      <View className="flex-row items-center justify-between">
        <Text className="text-md font-semibold text-ink-primary">{role}</Text>
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
            title={`Confirm ${role}`}
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
