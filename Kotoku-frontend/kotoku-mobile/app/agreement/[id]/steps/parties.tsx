import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { useEffect, useMemo, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from "react-native";
import { z } from "zod";
import { ShieldCheck, Users2 } from "lucide-react-native";

import { setParties } from "@/api/agreements";
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

  useEffect(() => {
    const needsRefresh = savedParties.some((party) =>
      party.ghanaCardFrontUploaded &&
      party.ghanaCardBackUploaded &&
      party.identitySelfieUploaded &&
      (party.identityVerificationStatus === "pending" ||
        party.identityVerificationStatus === "processing"),
    );
    if (!needsRefresh) return;
    const timer = setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
    }, 2500);
    return () => clearInterval(timer);
  }, [agreementId, queryClient, savedParties]);

  if (!template || isLoading) {
    return <ScreenLoader />;
  }

  const identityComplete =
    savedParties.length === roleKeys.length &&
    savedParties.every((party) => isPartyIdentityComplete(party));

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

  const handleSourcePick = async (source: "camera" | "library") => {
    if (!uploadSheet) return;
    const current = uploadSheet;
    setUploadSheet(null);
    await pickImage(current.slotId, current.evidenceType, {
      source,
      cameraType: current.cameraType,
    });
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
                Each party needs a phone number, Ghana Card PIN, confirmed Ghana Card images, and a selfie photo before you can continue.
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

        {savedParties.length === roleKeys.length && (
          <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
            <View className="flex-row items-start gap-md">
              <View className="h-10 w-10 items-center justify-center rounded-2xl bg-brand-primary/10">
                <ShieldCheck size={20} color="#2563EB" strokeWidth={1.8} />
              </View>
              <View className="flex-1 gap-xs">
                <Text className="text-base font-semibold text-ink-primary">Ghana Card uploads</Text>
                <Text className="text-sm text-ink-secondary leading-relaxed">
                  Upload the front and back of each Ghana Card, then capture a selfie photo. This step only completes after the backend confirms the files in storage and verifies the match.
                </Text>
              </View>
            </View>

            {savedParties.map((party) => {
              const frontEvidenceType = identityEvidenceType(party.role, "front");
              const backEvidenceType = identityEvidenceType(party.role, "back");
              const selfieEvidenceType = identityEvidenceType(party.role, "selfie");
              const frontItem = items[frontEvidenceType];
              const backItem = items[backEvidenceType];
              const selfieItem = items[selfieEvidenceType];
              return (
                <View key={party.id} className="gap-sm rounded-2xl border border-border-subtle bg-surface-subtle p-md">
                  <View className="gap-xs">
                    <Text className="text-sm font-semibold text-ink-primary">{party.displayName}</Text>
                    <Text className="text-xs text-ink-muted">
                      {party.idNumber}
                    </Text>
                    <Text
                      className={`text-xs ${
                        party.identityVerificationStatus === "verified"
                          ? "text-semantic-success"
                          : party.identityVerificationStatus === "failed" ||
                              party.identityVerificationStatus === "manual_review_required"
                            ? "text-semantic-error"
                          : "text-ink-muted"
                      }`}
                    >
                      {buildIdentityStatusMessage(party)}
                    </Text>
                  </View>
                  <View className="flex-row gap-sm">
                    <View style={{ flex: 1 }}>
                      <PhotoSlot
                        label="Ghana Card front"
                        required
                        localUri={frontItem?.localUri || party.ghanaCardFrontViewUrl || undefined}
                        status={frontItem?.uploadStatus || (party.ghanaCardFrontUploaded ? "uploaded" : "pending")}
                        error={frontItem?.error}
                        failedActionLabel={frontItem?.retryable === false ? "Replace" : "Retry"}
                        onPress={() => {
                          if (frontItem?.uploadStatus === "failed" && frontItem.retryable !== false) {
                            void retryUpload(frontEvidenceType);
                            return;
                          }
                          setUploadSheet({
                            slotId: frontEvidenceType,
                            evidenceType: frontEvidenceType,
                            title: "Ghana Card front",
                            body: "Add a clear image of the front of the Ghana Card for OCR and identity checks.",
                            guidance:
                              "Keep all card edges visible, avoid glare, and make sure the PIN and printed details are readable.",
                            cameraType: "back",
                          });
                        }}
                      />
                    </View>
                    <View style={{ flex: 1 }}>
                      <PhotoSlot
                        label="Ghana Card back"
                        required
                        localUri={backItem?.localUri || party.ghanaCardBackViewUrl || undefined}
                        status={backItem?.uploadStatus || (party.ghanaCardBackUploaded ? "uploaded" : "pending")}
                        error={backItem?.error}
                        failedActionLabel={backItem?.retryable === false ? "Replace" : "Retry"}
                        onPress={() => {
                          if (backItem?.uploadStatus === "failed" && backItem.retryable !== false) {
                            void retryUpload(backEvidenceType);
                            return;
                          }
                          setUploadSheet({
                            slotId: backEvidenceType,
                            evidenceType: backEvidenceType,
                            title: "Ghana Card back",
                            body: "Add a clear image of the back of the Ghana Card so the backend can verify the document details.",
                            guidance:
                              "Capture the full card on a flat background and avoid blur, shadows, and cropped corners.",
                            cameraType: "back",
                          });
                        }}
                      />
                    </View>
                  </View>
                  <View>
                    <PhotoSlot
                      label="Selfie photo"
                      required
                      localUri={selfieItem?.localUri || party.identitySelfieViewUrl || undefined}
                      status={selfieItem?.uploadStatus || (party.identitySelfieUploaded ? "uploaded" : "pending")}
                      error={selfieItem?.error}
                      failedActionLabel={selfieItem?.retryable === false ? "Retake" : "Retry"}
                      onPress={() => {
                        if (selfieItem?.uploadStatus === "failed" && selfieItem.retryable !== false) {
                          void retryUpload(selfieEvidenceType);
                          return;
                        }
                        setUploadSheet({
                          slotId: selfieEvidenceType,
                          evidenceType: selfieEvidenceType,
                          title: "Selfie photo",
                          body: "Capture or choose a clear selfie photo for face comparison against the Ghana Card portrait.",
                          guidance:
                            "Look straight at the camera, use good lighting, and keep hats, heavy shadows, and blur out of the frame.",
                          cameraType: "front",
                          cameraLabel: "Take selfie",
                        });
                      }}
                    />
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {saveError && <NoticeCard variant="error" title="Could not save parties" body={saveError} compact />}

        {uploadError && <NoticeCard variant="error" title="Upload needs attention" body={uploadError} compact />}

        {!identityComplete && savedParties.length === roleKeys.length && !formState.isDirty && (
          <Text className="text-xs text-ink-muted text-center">
            Finish the Ghana Card uploads, capture a selfie photo for each party, and wait for backend verification to continue.
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
