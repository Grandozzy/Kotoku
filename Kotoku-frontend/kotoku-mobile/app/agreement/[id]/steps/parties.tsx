import { zodResolver } from "@hookform/resolvers/zod";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useForm } from "react-hook-form";
import { ScrollView, Text, View } from "react-native";
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
    .regex(/^\+[1-9]\d{9,14}$/, "Enter a valid number with country code"),
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
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = useForm<PartiesFormValues>({
    resolver: zodResolver(partiesSchema),
    mode: "onChange",
    defaultValues: {
      partyA: partyA.fullName ? partyA : { fullName: "", phone: "", idType: "ghana_card", idNumber: "" },
      partyB: partyB.fullName ? partyB : { fullName: "", phone: "", idType: "ghana_card", idNumber: "" },
    },
  });

  const watchedA = watch("partyA");
  const watchedB = watch("partyB");

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
      {/* Party A */}
      <PartySection
        title={roleA}
        prefix="partyA"
        register={register}
        errors={errors.partyA}
        idType={watchedA?.idType ?? "ghana_card"}
        onIdTypeChange={(v) => setValue("partyA.idType", v)}
      />

      {/* Party B */}
      <PartySection
        title={roleB}
        prefix="partyB"
        register={register}
        errors={errors.partyB}
        idType={watchedB?.idType ?? "ghana_card"}
        onIdTypeChange={(v) => setValue("partyB.idType", v)}
      />

      <Button
        title="Next — Details"
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

import { Pressable } from "react-native";
import {
  UseFormRegister,
  FieldErrors,
  Path,
  RegisterOptions,
} from "react-hook-form";

interface PartySectionProps {
  title: string;
  prefix: "partyA" | "partyB";
  register: UseFormRegister<PartiesFormValues>;
  errors?: FieldErrors<PartiesFormValues["partyA"]>;
  idType: IdType;
  onIdTypeChange: (v: IdType) => void;
}

function PartySection({
  title,
  prefix,
  register,
  errors,
  idType,
  onIdTypeChange,
}: PartySectionProps) {
  return (
    <View className="gap-md">
      <Text className="text-lg font-semibold text-ink-primary">{title}</Text>

      <TextInput
        label="Full name"
        placeholder="As on ID document"
        required
        error={errors?.fullName?.message}
        {...register(`${prefix}.fullName`)}
      />
      <TextInput
        label="Phone number"
        placeholder="+233 XX XXX XXXX"
        keyboardType="phone-pad"
        required
        error={errors?.phone?.message}
        {...register(`${prefix}.phone`)}
      />

      {/* ID type selector */}
      <View className="gap-xs">
        <Text className="text-sm font-medium text-ink-secondary">
          ID type <Text className="text-semantic-error">*</Text>
        </Text>
        <View className="flex-row gap-sm">
          {ID_TYPE_OPTIONS.map((opt) => (
            <Pressable
              key={opt.value}
              onPress={() => onIdTypeChange(opt.value)}
              className={[
                "px-md py-sm rounded-pill border flex-1 items-center",
                idType === opt.value
                  ? "bg-brand-primary border-brand-primary"
                  : "bg-surface-card border-border-subtle",
              ].join(" ")}
            >
              <Text
                className={
                  idType === opt.value
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

      <TextInput
        label="ID number"
        placeholder="Enter ID number"
        required
        error={errors?.idNumber?.message}
        {...register(`${prefix}.idNumber`)}
      />
    </View>
  );
}
