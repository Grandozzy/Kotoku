import { zodResolver } from "@hookform/resolvers/zod";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Pressable, ScrollView, Text, View } from "react-native";
import { z } from "zod";

import { Button, TextInput } from "@/components/ui";
import {
  useAgreementStore,
  type IdType,
} from "@/features/agreements/agreementStore";
import { useTemplate } from "@/features/agreements/useAgreementDraft";

const partySchema = z.object({
  fullName: z.string().min(2, "Full name is required"),
  phone: z
    .string()
    .min(10, "Phone number is too short")
    .max(15, "Phone number is too long")
    .refine(
      (v) => /^(\+\d{10,15}|\d{10,15})$/.test(v.replace(/\s/g, "")),
      "Enter a valid phone number (e.g. +233501234567 or 0501234567)",
    ),
  idType: z.enum(["ghana_card", "passport", "other"]),
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
  { value: "other", label: "Other" },
];

export default function PartiesStep() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { scenarioId, partyA, partyB, setPartyA, setPartyB, nextStep } =
    useAgreementStore();
  const template = useTemplate(scenarioId);
  const [roleA, roleB] = template?.partyRoles ?? ["Party A", "Party B"];

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
  } = useForm<PartiesFormValues>({
    resolver: zodResolver(partiesSchema),
    mode: "onChange",
    defaultValues: {
      partyA: partyA.fullName ? partyA : { fullName: "", phone: "", idType: "ghana_card" as IdType, idNumber: "" },
      partyB: partyB.fullName ? partyB : { fullName: "", phone: "", idType: "ghana_card" as IdType, idNumber: "" },
    },
  });

  const onSubmit = (values: PartiesFormValues) => {
    setPartyA(values.partyA);
    setPartyB(values.partyB);
    nextStep();
    router.push(`/agreement/${id}/steps/details`);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
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

      <Button
        title="Proceed"
        variant="primary"
        size="lg"
        fullWidth
        disabled={!isValid}
        onPress={handleSubmit(onSubmit)}
      />
    </ScrollView>
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