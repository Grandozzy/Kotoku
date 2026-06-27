import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircle, Clock, RefreshCw, TrendingUp } from "lucide-react-native";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, OTPInput, ScreenLoader } from "@/components/ui";
import { useAgreementStore, type PartyDraft } from "@/features/agreements/agreementStore";
import {
  useConfirmOtp,
  useConsentStatus,
  useRequestOtp,
  getApiErrorMessage,
} from "@/features/consent/useConsentFlow";
import { useAgreement, useSealAgreement, useTemplate } from "@/features/agreements/useAgreementDraft";
import { usePlan } from "@/features/billing/usePlan";
import { isCapReachedError } from "@/lib/errorHandler";
import { isSamePhone } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";
import { colors } from "@/theme/tokens";

export default function ConsentStep() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const agreementId = Number(id);

  const { scenarioId, consentA, consentB, partyA, partyB } = useAgreementStore();
  const authenticatedPhone = useSessionStore((s) => s.phone);
  const template = useTemplate(scenarioId);
  const [roleA, roleB] = template?.partyRoles ?? ["Party A", "Party B"];

  const [codeA, setCodeA] = useState("");
  const [codeB, setCodeB] = useState("");

  const { data: plan } = usePlan();
  const agreementQuery = useAgreement(agreementId);
  const requestOtp = useRequestOtp(agreementId);
  const confirmOtp = useConfirmOtp(agreementId);
  const consentStatus = useConsentStatus(agreementId);
  const sealMutation = useSealAgreement(agreementId);
  const backendPartyA = agreementQuery.data?.parties[0];
  const backendPartyB = agreementQuery.data?.parties[1];
  const effectivePartyA: PartyDraft = partyA.phone
    ? partyA
    : backendPartyA
      ? {
          fullName: backendPartyA.displayName,
          phone: backendPartyA.phone,
          idType: backendPartyA.idType ?? "ghana_card",
          idNumber: backendPartyA.idNumber ?? "",
        }
      : partyA;
  const effectivePartyB: PartyDraft = partyB.phone
    ? partyB
    : backendPartyB
      ? {
          fullName: backendPartyB.displayName,
          phone: backendPartyB.phone,
          idType: backendPartyB.idType ?? "ghana_card",
          idNumber: backendPartyB.idNumber ?? "",
        }
      : partyB;
  const missingPartyContext = !effectivePartyA.phone || !effectivePartyB.phone;

  const records = consentStatus.data?.records ?? [];
  const latestRecords = [...records].sort((left, right) => {
    const leftCreatedAt = left.createdAt ? Date.parse(left.createdAt) : 0;
    const rightCreatedAt = right.createdAt ? Date.parse(right.createdAt) : 0;
    return rightCreatedAt - leftCreatedAt || right.id - left.id;
  });
  const partyARecord = latestRecords.find((record) => isSamePhone(record.partyPhone, effectivePartyA.phone));
  const partyBRecord = latestRecords.find((record) => isSamePhone(record.partyPhone, effectivePartyB.phone));
  const pendingRecords = [partyARecord, partyBRecord].filter(
    (record) => record && !record.granted,
  );
  const consentExpired =
    pendingRecords.length > 0 &&
    pendingRecords.some((record) => Date.parse(record!.expiresAt) <= Date.now());
  const hasBackendConsentRecords = (consentStatus.data?.records.length ?? 0) > 0;
  const otpsSent = hasBackendConsentRecords || (consentA.otpSent && consentB.otpSent);
  const activeOtpsSent = otpsSent && !consentExpired;
  const partyAConfirmed = otpsSent && (partyARecord?.granted ?? consentA.confirmed);
  const partyBConfirmed = otpsSent && (partyBRecord?.granted ?? consentB.confirmed);
  const bothConfirmed = activeOtpsSent && consentStatus.data?.allConsented === true;
  const currentParty =
    authenticatedPhone && isSamePhone(authenticatedPhone, effectivePartyA.phone)
      ? "A"
      : authenticatedPhone && isSamePhone(authenticatedPhone, effectivePartyB.phone)
        ? "B"
        : null;
  const currentPartyConfirmed =
    currentParty === "A"
      ? partyAConfirmed
      : currentParty === "B"
        ? partyBConfirmed
        : false;
  const onlyPartyAConfirmed = partyAConfirmed && !partyBConfirmed;
  const onlyPartyBConfirmed = partyBConfirmed && !partyAConfirmed;
  const otherPartyRole = currentParty === "A" ? roleB : roleA;

  // Cap state — either proactive (from plan hook) or reactive (from seal error)
  const proactiveCapReached = plan?.flags.is_personal && plan?.usage.is_cap_reached;
  const reactiveCapReached = sealMutation.isError && isCapReachedError(sealMutation.error);
  const capReached = proactiveCapReached || reactiveCapReached;
  const upgradeOption = plan?.recommended_upgrades[0];

  const handleRequestCodes = (validateBeforeRequest = true) => {
    requestOtp.mutate({ validateBeforeRequest });
  };

  const handleConfirmCurrentParty = () => {
    if (!currentParty) return;
    confirmOtp.mutate({
      party: currentParty,
      otpCode: currentParty === "A" ? codeA : codeB,
    });
  };

  const confirmError =
    confirmOtp.isError ? getApiErrorMessage(confirmOtp.error) : null;

  if (missingPartyContext && agreementQuery.isLoading) {
    return <ScreenLoader rows={4} />;
  }

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-surface-canvas"
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? 96 : 0}
    >
      <ScrollView
        className="flex-1"
        contentContainerClassName="px-lg py-xl gap-xl"
        contentContainerStyle={{ paddingBottom: insets.bottom + 180 }}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
        automaticallyAdjustKeyboardInsets
        refreshControl={
          <RefreshControl
            refreshing={consentStatus.isRefetching}
            onRefresh={() => consentStatus.refetch()}
            tintColor={colors.brandPrimary}
          />
        }
      >
      <View className="gap-sm">
        <Text className="text-xl font-semibold text-ink-primary">
          Confirm consent
        </Text>
        <Text className="text-md text-ink-secondary">
          Both parties must confirm with a one-time code sent to their phone
          before the agreement can be sealed.
        </Text>
        <View className="bg-blue-50 border border-blue-100 rounded-xl p-md gap-xs">
          <Text className="text-sm font-semibold text-blue-900">
            Each party confirms with their own OTP.
          </Text>
          <Text className="text-xs text-blue-800 leading-relaxed">
            The creator receives an OTP only. The other party receives their OTP
            plus a secure review link, so they can confirm without installing the
            app.
          </Text>
        </View>
      </View>

      {!otpsSent && (
        <Button
          title="Request consent codes"
          variant="primary"
          size="lg"
          fullWidth
          loading={requestOtp.isPending}
          onPress={() => handleRequestCodes()}
        />
      )}

      {requestOtp.isError && (!otpsSent || consentExpired) && (
        <Text className="text-sm text-semantic-error text-center">
          {getApiErrorMessage(requestOtp.error)}
        </Text>
      )}

      <ConsentProgressCard
        bothConfirmed={bothConfirmed}
        consentExpired={consentExpired}
        otpsSent={otpsSent}
        partyAConfirmed={partyAConfirmed}
        partyBConfirmed={partyBConfirmed}
        roleA={roleA}
        roleB={roleB}
      />

      {otpsSent && !bothConfirmed && (
        <View className="bg-surface-card border border-border-subtle rounded-xl p-md gap-sm">
          <View className="flex-row items-center gap-sm">
            <RefreshCw size={16} color={colors.inkSecondary} strokeWidth={2} />
            <Text className="text-sm font-semibold text-ink-primary flex-1">
              Waiting for consent updates
            </Text>
          </View>
          <Text className="text-xs text-ink-secondary leading-relaxed">
            Kotoku checks automatically. Pull down or tap refresh after the
            other party confirms from their link.
          </Text>
          <Button
            title="Refresh consent status"
            variant="secondary"
            size="md"
            fullWidth
            loading={consentStatus.isFetching}
            onPress={() => consentStatus.refetch()}
          />
        </View>
      )}

      {consentStatus.isError && (
        <View className="bg-rose-50 border border-rose-100 rounded-xl p-md gap-sm">
          <Text className="text-sm font-semibold text-rose-800">
            Could not refresh consent status
          </Text>
          <Text className="text-xs text-rose-700 leading-relaxed">
            {getApiErrorMessage(consentStatus.error)}
          </Text>
          <Button
            title="Try again"
            variant="secondary"
            size="md"
            fullWidth
            loading={consentStatus.isFetching}
            onPress={() => consentStatus.refetch()}
          />
        </View>
      )}

      {consentExpired && (
        <View className="bg-amber-50 border border-amber-200 rounded-xl p-md gap-md">
          <Text className="text-sm text-amber-900 leading-relaxed">
            These consent codes have expired. Request new codes so both parties
            can confirm within the active OTP window.
          </Text>
          <Button
            title="Request new consent codes"
            variant="primary"
            size="md"
            fullWidth
            loading={requestOtp.isPending}
            onPress={() => handleRequestCodes(false)}
          />
        </View>
      )}

      {otpsSent && (
        <View className="bg-surface-subtle border border-border-subtle rounded-xl p-md">
          <Text className="text-sm text-ink-secondary leading-relaxed">
            Consent has started, so agreement details are locked. If something is
            wrong, do not confirm; restart the agreement with corrected details.
          </Text>
        </View>
      )}

      {activeOtpsSent && !currentParty && (
        <View className="bg-amber-50 border border-amber-200 rounded-xl p-md">
          <Text className="text-sm text-amber-800 leading-relaxed">
            This signed-in phone is not one of the pending parties. Sign in with
            the phone number that received the OTP to confirm consent.
          </Text>
        </View>
      )}

      {activeOtpsSent && currentParty === "A" && (
        <ConsentPartyBlock
          role={roleA}
          phone={effectivePartyA.phone}
          confirmed={partyAConfirmed}
          code={codeA}
          onCodeChange={(v) => {
            setCodeA(v);
            if (confirmOtp.isError) confirmOtp.reset();
          }}
          onConfirm={handleConfirmCurrentParty}
          loading={confirmOtp.isPending}
          error={confirmError ?? undefined}
          disabled={partyAConfirmed}
        />
      )}

      {activeOtpsSent && currentParty === "B" && (
        <ConsentPartyBlock
          role={roleB}
          phone={effectivePartyB.phone}
          confirmed={partyBConfirmed}
          code={codeB}
          onCodeChange={(v) => {
            setCodeB(v);
            if (confirmOtp.isError) confirmOtp.reset();
          }}
          onConfirm={handleConfirmCurrentParty}
          loading={confirmOtp.isPending}
          error={confirmError ?? undefined}
          disabled={partyBConfirmed}
        />
      )}

      {activeOtpsSent && currentParty && currentPartyConfirmed && !bothConfirmed && (
        <View className="bg-emerald-50 border border-emerald-100 rounded-xl p-md">
          <Text className="text-sm text-emerald-800 leading-relaxed">
            Your consent is confirmed. Waiting for {otherPartyRole} to enter
            their OTP before this agreement can be sealed.
          </Text>
        </View>
      )}

      {activeOtpsSent && currentParty && !currentPartyConfirmed && !bothConfirmed && (
        <View className="bg-blue-50 border border-blue-100 rounded-xl p-md">
          <Text className="text-sm text-blue-800 leading-relaxed">
            Enter the OTP sent to your phone. The agreement can only be sealed
            after both parties have confirmed.
          </Text>
        </View>
      )}

      {activeOtpsSent && !currentParty && onlyPartyAConfirmed && !bothConfirmed && (
        <PendingPartyNotice confirmedRole={roleA} pendingRole={roleB} />
      )}

      {activeOtpsSent && !currentParty && onlyPartyBConfirmed && !bothConfirmed && (
        <PendingPartyNotice confirmedRole={roleB} pendingRole={roleA} />
      )}

      {bothConfirmed && (
        <View className="gap-md">
          <View className="flex-row items-center justify-center gap-sm bg-emerald-50 rounded-lg p-md">
            <CheckCircle size={18} color={colors.success} />
            <Text className="text-sm font-medium text-emerald-700">
              Both parties have confirmed
            </Text>
          </View>

          {/* Cap-reached blocker */}
          {capReached ? (
            <View className="bg-amber-50 border border-amber-200 rounded-xl p-lg gap-sm">
              <View className="flex-row items-center gap-sm">
                <TrendingUp size={16} color="#d97706" strokeWidth={2} />
                <Text className="text-sm font-semibold text-amber-900 flex-1">
                  Monthly sealing limit reached
                </Text>
              </View>
              <Text className="text-xs text-amber-700 leading-relaxed">
                You&apos;ve used all {plan?.plan.max_agreements_per_month} seals for this
                month on {plan?.plan.name ?? "your plan"}.
                {upgradeOption
                  ? ` Upgrade to ${upgradeOption.name} (${upgradeOption.price_amount_monthly} GHS/mo) for up to ${upgradeOption.max_agreements_per_month} seals.`
                  : " Wait until next month or upgrade your plan."}
              </Text>
            </View>
          ) : (
            <Button
              title="Seal agreement"
              variant="primary"
              size="lg"
              fullWidth
              loading={sealMutation.isPending}
              onPress={() => sealMutation.mutate()}
            />
          )}

          {sealMutation.isError && !capReached && (
            <Text className="text-sm text-semantic-error text-center">
              {getApiErrorMessage(sealMutation.error)}
            </Text>
          )}
        </View>
      )}

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function ConsentProgressCard({
  bothConfirmed,
  consentExpired,
  otpsSent,
  partyAConfirmed,
  partyBConfirmed,
  roleA,
  roleB,
}: {
  bothConfirmed: boolean;
  consentExpired: boolean;
  otpsSent: boolean;
  partyAConfirmed: boolean;
  partyBConfirmed: boolean;
  roleA: string;
  roleB: string;
}) {
  const message = bothConfirmed
    ? "Both parties have confirmed."
    : consentExpired
      ? "Consent codes have expired. Request new codes to continue."
    : !otpsSent
      ? "Both parties have not confirmed yet. Request consent codes to begin."
      : partyAConfirmed && !partyBConfirmed
        ? `${roleA} has confirmed. Waiting for ${roleB} to confirm.`
        : partyBConfirmed && !partyAConfirmed
          ? `${roleB} has confirmed. Waiting for ${roleA} to confirm.`
          : "Both parties have not confirmed yet.";

  return (
    <View
      className={[
        "rounded-xl border p-md gap-sm",
        bothConfirmed
          ? "bg-emerald-50 border-emerald-100"
          : consentExpired
            ? "bg-amber-50 border-amber-200"
          : "bg-blue-50 border-blue-100",
      ].join(" ")}
    >
      <Text
        className={[
          "text-sm font-semibold",
          bothConfirmed
            ? "text-emerald-800"
            : consentExpired
              ? "text-amber-900"
              : "text-blue-900",
        ].join(" ")}
      >
        {message}
      </Text>
      <View className="gap-xs">
        <ConsentProgressRow role={roleA} confirmed={partyAConfirmed} />
        <ConsentProgressRow role={roleB} confirmed={partyBConfirmed} />
      </View>
    </View>
  );
}

function ConsentProgressRow({
  role,
  confirmed,
}: {
  role: string;
  confirmed: boolean;
}) {
  return (
    <View className="flex-row items-center justify-between">
      <Text className="text-xs text-ink-secondary">{role}</Text>
      <View className="flex-row items-center gap-xs">
        {confirmed ? (
          <CheckCircle size={14} color={colors.success} />
        ) : (
          <Clock size={14} color={colors.inkMuted} />
        )}
        <Text
          className={[
            "text-xs font-medium",
            confirmed ? "text-emerald-700" : "text-ink-muted",
          ].join(" ")}
        >
          {confirmed ? "Confirmed" : "Pending"}
        </Text>
      </View>
    </View>
  );
}

function PendingPartyNotice({
  confirmedRole,
  pendingRole,
}: {
  confirmedRole: string;
  pendingRole: string;
}) {
  return (
    <View className="bg-emerald-50 border border-emerald-100 rounded-xl p-md">
      <Text className="text-sm text-emerald-800 leading-relaxed">
        {confirmedRole} has confirmed. Waiting for {pendingRole} to enter their
        OTP before this agreement can be sealed.
      </Text>
    </View>
  );
}

interface ConsentPartyBlockProps {
  role: string;
  phone: string;
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
  phone,
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
        <View>
          <Text className="text-md font-semibold text-ink-primary">{role}</Text>
          <Text className="text-xs text-ink-muted mt-xs">{phone}</Text>
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
