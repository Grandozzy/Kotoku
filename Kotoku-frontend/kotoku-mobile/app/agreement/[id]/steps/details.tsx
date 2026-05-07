import { zodResolver } from "@hookform/resolvers/zod";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { ScrollView, Text, View } from "react-native";
import { z } from "zod";

import { Button } from "@/components/ui";
import { FieldRenderer } from "@/components/agreement/FieldRenderer";
import {
  useAgreementStore,
  STEPS,
} from "@/features/agreements/agreementStore";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { updateAgreement } from "@/api/agreements";

function buildDetailsSchema(template: {
  fields: Record<string, { required: boolean; type: string }>;
}) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const [key, def] of Object.entries(template.fields)) {
    if (def.required) {
      if (def.type === "boolean") {
        shape[key] = z.boolean().refine((v) => v === true, "Required");
      } else if (def.type === "number" || def.type === "currency") {
        shape[key] = z.number({ required_error: "Required", invalid_type_error: "Enter a number" }).min(0.01, "Required");
      } else {
        shape[key] = z.string().min(1, "Required");
      }
    } else {
      if (def.type === "boolean") {
        shape[key] = z.boolean().optional().default(false);
      } else if (def.type === "number" || def.type === "currency") {
        shape[key] = z.number().optional().or(z.undefined());
      } else {
        shape[key] = z.string().optional().default("");
      }
    }
  }
  return z.object(shape);
}

export default function DetailsStep() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { scenarioId, subjectData, setSubjectData, nextStep, prevStep, stepIndex } =
    useAgreementStore();
  const template = useTemplate(scenarioId);

  if (!template) {
    return (
      <View className="flex-1 items-center justify-center">
        <Text className="text-ink-muted">Template not found.</Text>
      </View>
    );
  }

  const schema = buildDetailsSchema(template);

  const {
    control,
    handleSubmit,
    watch,
    formState: { errors, isValid },
  } = useForm<Record<string, unknown>>({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: subjectData,
  });

  const watchValues = watch();

  const onSubmit = async (values: Record<string, unknown>) => {
    setSubjectData(values);
    try {
      await updateAgreement(Number(id), { field_data: values });
    } catch {}
    nextStep();
    router.push(`/agreement/${id}/steps/evidence`);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
      contentContainerStyle={{ paddingBottom: 60 }}
      keyboardShouldPersistTaps="handled"
    >
      {template.detailSections.map((section) => (
        <View key={section.title} className="gap-md">
          <Text className="text-lg font-semibold text-ink-primary border-b border-border-subtle pb-sm">
            {section.title}
          </Text>

          {section.fields.map((fieldKey) => {
            const fieldDef = template.fields[fieldKey];
            if (!fieldDef) return null;
            return (
              <FieldRenderer
                key={fieldKey}
                name={fieldKey}
                field={fieldDef}
                control={control}
                error={(errors[fieldKey] as { message?: string })?.message}
                watchValues={watchValues}
              />
            );
          })}
        </View>
      ))}

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
            title="Proceed"
            variant="primary"
            size="lg"
            disabled={!isValid}
            onPress={handleSubmit(onSubmit)}
          />
        </View>
      </View>
    </ScrollView>
  );
}