import { zodResolver } from "@hookform/resolvers/zod";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { useState } from "react";
import { z } from "zod";

import { Button, TextInput } from "@/components/ui";
import {
  useAgreementStore,
  type IdType,
} from "@/features/agreements/agreementStore";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { setParties } from "@/api/agreements";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { normalizePhoneToE164 } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";

const partySchema = z.object({
  fullName: z
    .string()
    .refine(
      (v) => {
        const parts = v.trim().split(/\s+/).filter(Boolean);
        return parts.length >= 2 && parts.every((p) => p.length >= 2);
      },
      "Enter your full name as it appears on your ID (first and last name)",
    ),
  phone: z
    .string()
    .min(10, "Phone number is too short")
    .max(15, "Phone number is too long")
    .refine(
      (v) => /^(\+\d{10,15}|\d{10,15})$/.test(v.replace(/\s/g, "")),
      "Enter a valid phone number (e.g. +233501234567 or 0501234567)",
    ),
  idType: z.enum(["ghana_card", "passport", "national_id"]),
  idNumber: z.string().min(3, "ID number is required"),
});

const partiesSchema = z.object({
  partyA: partySchema,
  partyB: partySchema,
});

type PartiesFormValues = z.infer<typeof partiesSchema>;

const ID_TYPE_OPTIONS: { value: IdType; label: string }[] = [
  { value: "ghana_card", label: "Ghana Card" },
  { value: "passport", label: "Passport" },
  { value: "national_id", label: "National ID Card" },
];

export default function PartiesStep() {
  const router = useRouter();
  const { id, scenarioId: urlScenarioId } = useLocalSearchParams<{ id: string; scenarioId?: string }>();
  const storeScenarioId = useAgreementStore((s) => s.scenarioId);
  const scenarioId = storeScenarioId ?? urlScenarioId ?? null;
  const agreementId = Number(id);
  const { partyA, partyB, setPartyA, setPartyB, goToStep } =
    useAgreementStore();
  const creatorPhone = useSessionStore((s) => s.phone);
  const template = useTemplate(scenarioId);

  const [roleA, roleB] = template?.partyRoles ?? ["Buyer", "Seller"];
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const roleEnum = (label: string) => label.toLowerCase();

  const emptyParty = { fullName: "", phone: "", idType: "ghana_card" as IdType, idNumber: "" };
  const hasPartyDraft = (party: typeof partyA) =>
    Boolean(party.fullName || party.phone || party.idNumber);

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
  } = useForm<PartiesFormValues>({
    resolver: zodResolver(partiesSchema),
    mode: "onChange",
    defaultValues: {
      partyA: hasPartyDraft(partyA)
        ? partyA
        : { ...emptyParty, phone: creatorPhone ?? "" },
      partyB: hasPartyDraft(partyB) ? partyB : emptyParty,
    },
  });

  const onSubmit = async (values: PartiesFormValues) => {
    setSaveError(null);
    const normalizedPartyA = {
      ...values.partyA,
      phone: normalizePhoneToE164(values.partyA.phone),
    };
    const normalizedPartyB = {
      ...values.partyB,
      phone: normalizePhoneToE164(values.partyB.phone),
    };
    setSaving(true);
    try {
      await setParties(agreementId, [
        {
          role: roleEnum(roleA),
          full_name: normalizedPartyA.fullName,
          phone: normalizedPartyA.phone,
          id_type: normalizedPartyA.idType,
          id_number: normalizedPartyA.idNumber,
        },
        {
          role: roleEnum(roleB),
          full_name: normalizedPartyB.fullName,
          phone: normalizedPartyB.phone,
          id_type: normalizedPartyB.idType,
          id_number: normalizedPartyB.idNumber,
        },
      ]);
      setPartyA(normalizedPartyA);
      setPartyB(normalizedPartyB);
    } catch (error) {
      setSaveError(getApiErrorMessage(error, "Could not save parties. Check your access and party details."));
      setSaving(false);
      return;
    }
    setSaving(false);
    goToStep(1);
    router.push(`/agreement/${id}/steps/details?scenarioId=${scenarioId}`);
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
        <PartySection
          title={roleA}
          prefix="partyA"
          control={control}
          errors={errors.partyA}
        />

        <PartySection
          title={roleB}
          prefix="partyB"
          control={control}
          errors={errors.partyB}
        />

        <View className="flex-row gap-sm">
          <View style={{ flex: 2 }}>
            <Button
              title="Proceed"
              variant="primary"
              size="lg"
              disabled={!isValid || saving}
              loading={saving}
              onPress={handleSubmit(onSubmit)}
            />
          </View>
        </View>
        {saveError && (
          <Text className="text-sm text-semantic-error text-center">
            {saveError}
          </Text>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ---------- Sub-component ----------

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
    <View className="gap-md">
      <Text className="text-lg font-semibold text-ink-primary">{title}</Text>

      <Controller
        control={control}
        name={`${prefix}.fullName` as const}
        render={({ field: { onChange, value } }) => (
          <TextInput
            label="Full name"
            placeholder="As on ID document"
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

      <Controller
        control={control}
        name={`${prefix}.idType` as const}
        render={({ field: { onChange, value } }) => (
          <View className="gap-xs">
            <Text className="text-sm font-medium text-ink-secondary">
              ID type <Text className="text-semantic-error">*</Text>
            </Text>
            <View className="flex-row gap-sm">
              {ID_TYPE_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.value}
                  onPress={() => onChange(opt.value)}
                  className={[
                    "px-md py-sm rounded-pill border flex-1 items-center",
                    value === opt.value
                      ? "bg-brand-primary border-brand-primary"
                      : "bg-surface-card border-border-subtle",
                  ].join(" ")}
                >
                  <Text
                    className={
                      value === opt.value
                        ? "text-xs font-medium text-white"
                        : "text-xs text-ink-primary"
                    }
                  >
                    {opt.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}
      />

      <Controller
        control={control}
        name={`${prefix}.idNumber` as const}
        render={({ field: { onChange, value } }) => (
          <TextInput
            label="ID number"
            placeholder="Enter ID number"
            required
            error={errors?.idNumber?.message}
            value={value}
            onChangeText={onChange}
          />
        )}
      />
    </View>
  );
}
