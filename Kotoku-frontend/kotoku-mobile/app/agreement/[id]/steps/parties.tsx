import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { z } from "zod";
import {
  CheckCircle2,
  Clock,
  Mail,
  ScanFace,
  ShieldCheck,
  Users2,
  XCircle,
} from "lucide-react-native";

import {
  createLivenessSession,
  sendPartyIdentityInvite,
  setParties,
  submitLivenessResult,
} from "@/api/agreements";
import { LivenessWebView } from "@/components/identity/LivenessWebView";
import { PhotoSlot } from "@/components/evidence/PhotoSlot";
import { UploadSourceSheet } from "@/components/evidence/UploadSourceSheet";
import { Button, NoticeCard, ScreenLoader, TextInput } from "@/components/ui";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import {
  buildIdentityStatusMessage,
  GHANA_CARD_PIN_REGEX,
  formatGhanaCardPin,
  identityEvidenceType,
  isPartyIdentityComplete,
  normalizeGhanaCardPin,
} from "@/features/agreements/partyIdentity";
import { useAgreement, useTemplate } from "@/features/agreements/useAgreementDraft";
import { useEvidenceUpload } from "@/features/evidence/useEvidenceUpload";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { normalizePhoneToE164 } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";

const partySchema = z.object({
  fullName: z
    .string()
    .refine(
      (value) => {
        const parts = value.trim().split(/\s+/).filter(Boolean);
        return parts.length >= 2 && parts.every((part) => part.length >= 2);
      },
      "Enter the full name as it appears on the Ghana Card.",
    ),
  phone: z
    .string()
    .min(10, "Phone number is too short")
    .max(15, "Phone number is too long")
    .refine(
      (value) => /^(\+\d{10,15}|\d{10,15})$/.test(value.replace(/\s/g, "")),
      "Enter a valid phone number (e.g. +233501234567 or 0501234567)",
    ),
  idNumber: z
    .string()
    .transform((value) => normalizeGhanaCardPin(value))
    .refine(
      (value) => GHANA_CARD_PIN_REGEX.test(value),
      "Use the Ghana Card PIN format GHA-000000000-0",
    ),
});

const partiesSchema = z
  .object({
    partyA: partySchema,
    partyB: partySchema,
  })
  .refine(
    (value) => value.partyA.idNumber !== value.partyB.idNumber,
    {
      message: "Buyer and seller cannot share the same Ghana Card PIN.",
      path: ["partyB", "idNumber"],
    },
  );

type PartiesFormValues = z.infer<typeof partiesSchema>;

function toDraftParty(party?: {
  displayName: string;
  phone: string;
  idNumber: string;
} | null) {
  return {
    fullName: party?.displayName ?? "",
    phone: party?.phone ?? "",
    idNumber: party?.idNumber ?? "",
  };
}

interface UploadSheetState {
  slotId: string;
  evidenceType: string;
  title: string;
  body: string;
  guidance: string;
  cameraType: "front" | "back";
  cameraLabel?: string;
  libraryLabel?: string;
}

export default function PartiesStep() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id, scenarioId: urlScenarioId } = useLocalSearchParams<{ id: string; scenarioId?: string }>();
  const agreementId = Number(id);
  const creatorPhone = useSessionStore((state) => state.phone);
  const storeScenarioId = useAgreementStore((state) => state.scenarioId);
  const scenarioId = storeScenarioId ?? urlScenarioId ?? null;
  const { partyA, partyB, setPartyA, setPartyB, goToStep } = useAgreementStore();
  const template = useTemplate(scenarioId);
  const { data: agreement, isLoading } = useAgreement(agreementId);
  const { items, pickImage, retryUpload, error: uploadError } = useEvidenceUpload(agreementId);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [uploadSheet, setUploadSheet] = useState<UploadSheetState | null>(null);
  const [livenessSession, setLivenessSession] = useState<{ role: string; sessionId: string; region: string } | null>(null);
  const [livenessLoading, setLivenessLoading] = useState<string | null>(null);
  const [livenessError, setLivenessError] = useState<string | null>(null);
  const [inviteSending, setInviteSending] = useState(false);
  const [inviteSent, setInviteSent] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const processingResult = useRef(false);

  const roles = template?.partyRoles ?? ["Seller", "Buyer"];
  const roleKeys = useMemo(
    () => roles.map((role) => role.toLowerCase() as "buyer" | "seller" | "landlord" | "tenant"),
    [roles],
  );

  const savedParties = useMemo(() => {
    if (!agreement) return [];
    return roleKeys
      .map((role) => agreement.parties.find((party) => party.role === role))
      .filter((party): party is NonNullable<typeof party> => Boolean(party));
  }, [agreement, roleKeys]);

  // Party A = creator's party (phone matches); Party B = the counterparty.
  const myParty = useMemo(
    () => savedParties.find((p) => p.phone === creatorPhone) ?? savedParties[0] ?? null,
    [savedParties, creatorPhone],
  );
  const counterParty = useMemo(
    () => savedParties.find((p) => p !== myParty) ?? null,
    [savedParties, myParty],
  );

  const form = useForm<PartiesFormValues>({
    resolver: zodResolver(partiesSchema),
    mode: "onChange",
    defaultValues: {
      partyA: {
        fullName: partyA.fullName,
        phone: partyA.phone || creatorPhone || "",
        idNumber: partyA.idNumber,
      },
      partyB: {
        fullName: partyB.fullName,
        phone: partyB.phone,
        idNumber: partyB.idNumber,
      },
    },
  });

  const { control, handleSubmit, reset, formState } = form;

  useEffect(() => {
    if (savedParties.length < 2) return;
    reset({
      partyA: toDraftParty(savedParties[0]),
      partyB: toDraftParty(savedParties[1]),
    });
    setPartyA({
      fullName: savedParties[0].displayName,
      phone: savedParties[0].phone,
      idType: "ghana_card",
      idNumber: savedParties[0].idNumber,
    });
    setPartyB({
      fullName: savedParties[1].displayName,
      phone: savedParties[1].phone,
      idType: "ghana_card",
      idNumber: savedParties[1].idNumber,
    });
  }, [reset, savedParties, setPartyA, setPartyB]);

  // Poll while own party is processing.
  useEffect(() => {
    if (!myParty) return;
    const frontType = identityEvidenceType(myParty.role, "front");
    const backType = identityEvidenceType(myParty.role, "back");
    const frontDone = myParty.ghanaCardFrontUploaded || items[frontType]?.uploadStatus === "uploaded";
    const backDone = myParty.ghanaCardBackUploaded || items[backType]?.uploadStatus === "uploaded";
    const livenessDone = myParty.livenessStatus === "passed" || myParty.identitySelfieUploaded;
    const needsRefresh =
      frontDone &&
      backDone &&
      livenessDone &&
      (myParty.identityVerificationStatus === "pending" ||
        myParty.identityVerificationStatus === "processing");
    if (!needsRefresh) return;
    const timer = setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
    }, 2500);
    return () => clearInterval(timer);
  }, [agreementId, queryClient, myParty, items]);

  // Poll counterparty status so Party A sees when Party B completes.
  // Only poll in "pending" state once the invite has been sent in this session;
  // always poll in "processing" (Party B has uploaded and verification is running).
  useEffect(() => {
    if (!counterParty) return;
    const shouldPoll =
      counterParty.identityVerificationStatus === "processing" ||
      (counterParty.identityVerificationStatus === "pending" && inviteSent);
    if (!shouldPoll) return;
    const timer = setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
    }, 5000);
    return () => clearInterval(timer);
  }, [agreementId, queryClient, counterParty, inviteSent]);

  if (!template || isLoading) {
    return <ScreenLoader />;
  }

  const myIdentityComplete = myParty ? isPartyIdentityComplete(myParty) : false;
  const counterIdentityComplete = counterParty ? isPartyIdentityComplete(counterParty) : false;
  const identityComplete = myIdentityComplete && counterIdentityComplete;

  const handleSaveParties = async (values: PartiesFormValues) => {
    setSaveError(null);
    setSaving(true);
    const normalizedPartyA = {
      fullName: values.partyA.fullName.trim(),
      phone: normalizePhoneToE164(values.partyA.phone),
      idType: "ghana_card" as const,
      idNumber: normalizeGhanaCardPin(values.partyA.idNumber),
    };
    const normalizedPartyB = {
      fullName: values.partyB.fullName.trim(),
      phone: normalizePhoneToE164(values.partyB.phone),
      idType: "ghana_card" as const,
      idNumber: normalizeGhanaCardPin(values.partyB.idNumber),
    };

    try {
      await setParties(agreementId, [
        {
          role: roleKeys[0],
          full_name: normalizedPartyA.fullName,
          phone: normalizedPartyA.phone,
          id_type: normalizedPartyA.idType,
          id_number: normalizedPartyA.idNumber,
        },
        {
          role: roleKeys[1],
          full_name: normalizedPartyB.fullName,
          phone: normalizedPartyB.phone,
          id_type: normalizedPartyB.idType,
          id_number: normalizedPartyB.idNumber,
        },
      ]);
      setPartyA(normalizedPartyA);
      setPartyB(normalizedPartyB);
      await queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
      reset(
        {
          partyA: {
            fullName: normalizedPartyA.fullName,
            phone: normalizedPartyA.phone,
            idNumber: normalizedPartyA.idNumber,
          },
          partyB: {
            fullName: normalizedPartyB.fullName,
            phone: normalizedPartyB.phone,
            idNumber: normalizedPartyB.idNumber,
          },
        },
        { keepDirty: false, keepTouched: false },
      );
    } catch (error) {
      setSaveError(
        getApiErrorMessage(
          error,
          "Could not save parties. Check the Ghana Card PINs and phone numbers.",
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleProceed = handleSubmit(async (values) => {
    const hasSavedParties = savedParties.length === roleKeys.length;
    if (!hasSavedParties || formState.isDirty) {
      await handleSaveParties(values);
      return;
    }
    if (!identityComplete) {
      return;
    }
    goToStep(1);
    router.push(`/agreement/${id}/steps/details?scenarioId=${scenarioId}`);
  });

  const handleStartLiveness = async (role: string) => {
    setLivenessError(null);
    setLivenessLoading(role);
    try {
      const { session_id, region } = await createLivenessSession(agreementId, role);
      setLivenessSession({ role, sessionId: session_id, region });
    } catch {
      setLivenessError("Could not start face check. Please try again.");
    } finally {
      setLivenessLoading(null);
    }
  };

  const handleLivenessComplete = async () => {
    if (!livenessSession || processingResult.current) return;
    processingResult.current = true;
    const { role } = livenessSession;
    setLivenessSession(null);
    try {
      await submitLivenessResult(agreementId, role);
      await queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
    } catch {
      setLivenessError("Face check result could not be retrieved. Please try again.");
    } finally {
      processingResult.current = false;
    }
  };

  const handleLivenessError = (message: string) => {
    setLivenessSession(null);
    processingResult.current = false;
    setLivenessError(message);
  };

  const handleSourcePick = async (source: "camera" | "library") => {
    if (!uploadSheet) return;
    const current = uploadSheet;
    setUploadSheet(null);
    await pickImage(current.slotId, current.evidenceType, {
      source,
      cameraType: current.cameraType,
    });
  };

  const handleSendInvite = async () => {
    if (!counterParty) return;
    setInviteError(null);
    setInviteSending(true);
    try {
      await sendPartyIdentityInvite(agreementId, counterParty.role);
      setInviteSent(true);
    } catch (err) {
      setInviteError(getApiErrorMessage(err, "Could not send the invite. Please try again."));
    } finally {
      setInviteSending(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        className="flex-1 bg-surface-canvas"
        contentContainerClassName="px-lg py-xl gap-xl"
        contentContainerStyle={{ paddingBottom: 60 }}
        keyboardShouldPersistTaps="handled"
      >
        <View className="gap-md rounded-3xl bg-ink-primary p-lg">
          <View className="flex-row items-start gap-md">
            <View className="h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
              <Users2 size={22} color="#fff" strokeWidth={1.8} />
            </View>
            <View className="flex-1 gap-xs">
              <Text className="text-[11px] font-semibold uppercase tracking-[2px] text-white/60">
                Step 1
              </Text>
              <Text className="text-xl font-semibold text-white">Set up both parties</Text>
              <Text className="text-sm leading-relaxed text-white/75">
                Enter both parties' details, then each party completes their own Ghana Card and face check on their own device.
              </Text>
            </View>
          </View>
        </View>

        <PartySection
          title={roles[0]}
          prefix="partyA"
          control={control}
          errors={formState.errors.partyA}
        />

        <PartySection
          title={roles[1]}
          prefix="partyB"
          control={control}
          errors={formState.errors.partyB}
        />

        {/* Own identity verification — only shown for Party A (the creator) */}
        {savedParties.length === roleKeys.length && myParty && (
          <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
            <View className="flex-row items-start gap-md">
              <View className="h-10 w-10 items-center justify-center rounded-2xl bg-brand-primary/10">
                <ShieldCheck size={20} color="#2563EB" strokeWidth={1.8} />
              </View>
              <View className="flex-1 gap-xs">
                <Text className="text-base font-semibold text-ink-primary">Your Ghana Card verification</Text>
                <Text className="text-sm text-ink-secondary leading-relaxed">
                  Upload the front and back of your Ghana Card, then complete the face check.
                </Text>
              </View>
            </View>

            <View className="gap-sm rounded-2xl border border-border-subtle bg-surface-subtle p-md">
              <View className="gap-xs">
                <Text className="text-sm font-semibold text-ink-primary">{myParty.displayName}</Text>
                <Text className="text-xs text-ink-muted">{myParty.idNumber}</Text>
                <Text
                  className={`text-xs ${
                    myParty.identityVerificationStatus === "verified"
                      ? "text-semantic-success"
                      : myParty.identityVerificationStatus === "failed" ||
                          myParty.identityVerificationStatus === "manual_review_required"
                        ? "text-semantic-error"
                      : "text-ink-muted"
                  }`}
                >
                  {buildIdentityStatusMessage(myParty)}
                </Text>
              </View>

              <View className="flex-row gap-sm">
                <View style={{ flex: 1 }}>
                  <PhotoSlot
                    label="Ghana Card front"
                    required
                    localUri={items[identityEvidenceType(myParty.role, "front")]?.localUri || myParty.ghanaCardFrontViewUrl || undefined}
                    status={items[identityEvidenceType(myParty.role, "front")]?.uploadStatus || (myParty.ghanaCardFrontUploaded ? "uploaded" : "pending")}
                    error={items[identityEvidenceType(myParty.role, "front")]?.error}
                    failedActionLabel={items[identityEvidenceType(myParty.role, "front")]?.retryable === false ? "Replace" : "Retry"}
                    onPress={() => {
                      const frontType = identityEvidenceType(myParty.role, "front");
                      if (items[frontType]?.uploadStatus === "failed" && items[frontType].retryable !== false) {
                        void retryUpload(frontType);
                        return;
                      }
                      setUploadSheet({
                        slotId: frontType,
                        evidenceType: frontType,
                        title: "Ghana Card front",
                        body: "Add a clear image of the front of your Ghana Card.",
                        guidance: "Keep all card edges visible, avoid glare, and make sure the PIN and printed details are readable.",
                        cameraType: "back",
                      });
                    }}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <PhotoSlot
                    label="Ghana Card back"
                    required
                    localUri={items[identityEvidenceType(myParty.role, "back")]?.localUri || myParty.ghanaCardBackViewUrl || undefined}
                    status={items[identityEvidenceType(myParty.role, "back")]?.uploadStatus || (myParty.ghanaCardBackUploaded ? "uploaded" : "pending")}
                    error={items[identityEvidenceType(myParty.role, "back")]?.error}
                    failedActionLabel={items[identityEvidenceType(myParty.role, "back")]?.retryable === false ? "Replace" : "Retry"}
                    onPress={() => {
                      const backType = identityEvidenceType(myParty.role, "back");
                      if (items[backType]?.uploadStatus === "failed" && items[backType].retryable !== false) {
                        void retryUpload(backType);
                        return;
                      }
                      setUploadSheet({
                        slotId: backType,
                        evidenceType: backType,
                        title: "Ghana Card back",
                        body: "Add a clear image of the back of your Ghana Card.",
                        guidance: "Capture the full card on a flat background and avoid blur, shadows, and cropped corners.",
                        cameraType: "back",
                      });
                    }}
                  />
                </View>
              </View>

              <TouchableOpacity
                disabled={livenessLoading === myParty.role || myParty.livenessStatus === "passed"}
                onPress={() => void handleStartLiveness(myParty.role)}
                className={`flex-row items-center gap-sm rounded-xl border p-md ${
                  myParty.livenessStatus === "passed"
                    ? "border-semantic-success/30 bg-semantic-success/10"
                    : myParty.livenessStatus === "failed"
                      ? "border-semantic-error/30 bg-semantic-error/10"
                      : "border-border-subtle bg-surface-card"
                }`}
              >
                <View className="h-10 w-10 items-center justify-center rounded-xl bg-brand-primary/10">
                  {myParty.livenessStatus === "passed" ? (
                    <CheckCircle2 size={20} color="#16a34a" strokeWidth={1.8} />
                  ) : myParty.livenessStatus === "failed" ? (
                    <XCircle size={20} color="#dc2626" strokeWidth={1.8} />
                  ) : (
                    <ScanFace size={20} color="#2563EB" strokeWidth={1.8} />
                  )}
                </View>
                <View className="flex-1">
                  <Text className="text-sm font-semibold text-ink-primary">
                    {myParty.livenessStatus === "passed"
                      ? "Face check passed"
                      : myParty.livenessStatus === "failed"
                        ? "Face check failed — tap to retry"
                        : livenessLoading === myParty.role
                          ? "Starting face check…"
                          : "Start face check"}
                  </Text>
                  {myParty.livenessStatus !== "passed" && (
                    <Text className="text-xs text-ink-muted">
                      {livenessLoading === myParty.role
                        ? "Preparing camera…"
                        : "Follow the on-screen prompts to confirm your identity"}
                    </Text>
                  )}
                </View>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Counterparty identity — invite to verify on their own device */}
        {savedParties.length === roleKeys.length && counterParty && (
          <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
            <View className="flex-row items-start gap-md">
              <View className="h-10 w-10 items-center justify-center rounded-2xl bg-brand-primary/10">
                <Mail size={20} color="#2563EB" strokeWidth={1.8} />
              </View>
              <View className="flex-1 gap-xs">
                <Text className="text-base font-semibold text-ink-primary">
                  {counterParty.displayName}'s verification
                </Text>
                <Text className="text-sm text-ink-secondary leading-relaxed">
                  {counterIdentityComplete
                    ? `${counterParty.displayName} has completed their identity verification.`
                    : `Send ${counterParty.displayName} an invite so they can verify their own Ghana Card and face on their device.`}
                </Text>
              </View>
            </View>

            <View className="rounded-2xl border border-border-subtle bg-surface-subtle p-md gap-xs">
              <Text className="text-sm font-semibold text-ink-primary">{counterParty.displayName}</Text>
              <Text className="text-xs text-ink-muted">{counterParty.idNumber}</Text>
              <Text
                className={`text-xs ${
                  counterParty.identityVerificationStatus === "verified"
                    ? "text-semantic-success"
                    : counterParty.identityVerificationStatus === "failed" ||
                        counterParty.identityVerificationStatus === "manual_review_required"
                      ? "text-semantic-error"
                    : "text-ink-muted"
                }`}
              >
                {counterIdentityComplete
                  ? "Identity verified"
                  : buildIdentityStatusMessage(counterParty)}
              </Text>
            </View>

            {!counterIdentityComplete && (
              <TouchableOpacity
                disabled={inviteSending}
                onPress={() => void handleSendInvite()}
                className={`flex-row items-center gap-sm rounded-xl border p-md ${
                  inviteSent
                    ? "border-semantic-success/30 bg-semantic-success/10"
                    : "border-border-subtle bg-surface-card"
                }`}
              >
                <View className="h-10 w-10 items-center justify-center rounded-xl bg-brand-primary/10">
                  {inviteSent ? (
                    <CheckCircle2 size={20} color="#16a34a" strokeWidth={1.8} />
                  ) : (
                    <Clock size={20} color="#2563EB" strokeWidth={1.8} />
                  )}
                </View>
                <View className="flex-1">
                  <Text className="text-sm font-semibold text-ink-primary">
                    {inviteSending
                      ? "Sending invite…"
                      : inviteSent
                        ? "Invite sent — tap to resend"
                        : `Invite ${counterParty.displayName} to verify`}
                  </Text>
                  <Text className="text-xs text-ink-muted">
                    {inviteSent
                      ? `A link was sent to ${counterParty.phone}`
                      : "They will receive an SMS with a secure link"}
                  </Text>
                </View>
              </TouchableOpacity>
            )}

            {counterIdentityComplete && (
              <View className="flex-row items-center gap-sm rounded-xl border border-semantic-success/30 bg-semantic-success/10 p-md">
                <View className="h-10 w-10 items-center justify-center rounded-xl bg-semantic-success/10">
                  <CheckCircle2 size={20} color="#16a34a" strokeWidth={1.8} />
                </View>
                <Text className="flex-1 text-sm font-semibold text-semantic-success">
                  {counterParty.displayName}'s identity verified
                </Text>
              </View>
            )}
          </View>
        )}

        {livenessError && (
          <NoticeCard variant="error" title="Face check error" body={livenessError} compact />
        )}

        {inviteError && (
          <NoticeCard variant="error" title="Could not send invite" body={inviteError} compact />
        )}

        {saveError && <NoticeCard variant="error" title="Could not save parties" body={saveError} compact />}

        {uploadError && <NoticeCard variant="error" title="Upload needs attention" body={uploadError} compact />}

        {!identityComplete && savedParties.length === roleKeys.length && !formState.isDirty && (
          <Text className="text-xs text-ink-muted text-center">
            {!myIdentityComplete
              ? "Complete your Ghana Card uploads and face check above."
              : "Waiting for the other party to complete their identity verification."}
          </Text>
        )}

        <View className="flex-row gap-sm">
          <View style={{ flex: 2 }}>
            <Button
              title={savedParties.length === roleKeys.length && !formState.isDirty ? "Proceed" : "Save parties"}
              variant="primary"
              size="lg"
              disabled={!formState.isValid || saving || (!formState.isDirty && !identityComplete && savedParties.length === roleKeys.length)}
              loading={saving}
              onPress={() => {
                void handleProceed();
              }}
            />
          </View>
        </View>
      </ScrollView>

      {livenessSession && (
        <LivenessWebView
          sessionId={livenessSession.sessionId}
          region={livenessSession.region}
          onComplete={() => void handleLivenessComplete()}
          onError={handleLivenessError}
          onClose={() => setLivenessSession(null)}
        />
      )}

      <UploadSourceSheet
        visible={Boolean(uploadSheet)}
        onClose={() => setUploadSheet(null)}
        title={uploadSheet?.title ?? "Add photo"}
        body={uploadSheet?.body ?? "Choose how to add this photo."}
        guidance={uploadSheet?.guidance}
        cameraLabel={uploadSheet?.cameraLabel}
        libraryLabel={uploadSheet?.libraryLabel}
        onPickCamera={() => {
          void handleSourcePick("camera");
        }}
        onPickLibrary={() => {
          void handleSourcePick("library");
        }}
      />
    </KeyboardAvoidingView>
  );
}

import type { Control, FieldErrors } from "react-hook-form";

interface PartySectionProps {
  title: string;
  prefix: "partyA" | "partyB";
  control: Control<PartiesFormValues>;
  errors?: FieldErrors<PartiesFormValues["partyA"]>;
}

function PartySection({
  title,
  prefix,
  control,
  errors,
}: PartySectionProps) {
  return (
    <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
      <View className="gap-xs">
        <Text className="text-[11px] font-semibold uppercase tracking-[2px] text-ink-muted">
          Party
        </Text>
        <Text className="text-lg font-semibold text-ink-primary">{title}</Text>
      </View>

      <Controller
        control={control}
        name={`${prefix}.fullName` as const}
        render={({ field: { onChange, value } }) => (
          <TextInput
            label="Full name"
            placeholder="As shown on Ghana Card"
            required
            error={errors?.fullName?.message}
            value={value}
            onChangeText={onChange}
          />
        )}
      />

      <Controller
        control={control}
        name={`${prefix}.phone` as const}
        render={({ field: { onChange, value } }) => (
          <TextInput
            label="Phone number"
            placeholder="+233501234567 or 0501234567"
            keyboardType="phone-pad"
            required
            error={errors?.phone?.message}
            value={value}
            onChangeText={onChange}
          />
        )}
      />

      <View className="gap-xs">
        <Text className="text-sm font-medium text-ink-secondary">
          ID type <Text className="text-semantic-error">*</Text>
        </Text>
        <View className="rounded-xl border border-border-subtle bg-surface-subtle px-md py-md">
          <Text className="text-sm text-ink-primary">Ghana Card</Text>
        </View>
      </View>

      <Controller
        control={control}
        name={`${prefix}.idNumber` as const}
        render={({ field: { onChange, value } }) => (
          <TextInput
            label="Ghana Card PIN"
            placeholder="GHA-123456789-0"
            required
            error={errors?.idNumber?.message}
            value={value}
            onChangeText={(text) => onChange(formatGhanaCardPin(text))}
            autoCapitalize="characters"
            keyboardType="numeric"
          />
        )}
      />
    </View>
  );
}
