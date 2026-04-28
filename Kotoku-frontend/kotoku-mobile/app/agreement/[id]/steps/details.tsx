import { useLocalSearchParams, useRouter } from "expo-router";
import { useForm } from "react-hook-form";
import { ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui";
import { FieldRenderer } from "@/components/agreement/FieldRenderer";
import {
  useAgreementStore,
} from "@/features/agreements/agreementStore";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { getMissingRequiredFields } from "@/features/agreements/stepValidation";

export default function DetailsStep() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { scenarioId, subjectData, setSubjectData, nextStep } =
    useAgreementStore();
  const template = useTemplate(scenarioId);

  const {
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<Record<string, unknown>>({
    defaultValues: subjectData,
  });

  const watchValues = watch();

  if (!template) {
    return (
      <View className="flex-1 items-center justify-center">
        <Text className="text-ink-muted">Template not found.</Text>
      </View>
    );
  }

  // Collect all required field keys from the template
  const requiredFieldKeys = Object.entries(template.fields)
    .filter(([, def]) => def.required)
    .map(([key]) => key);

  const onSubmit = (values: Record<string, unknown>) => {
    const missing = getMissingRequiredFields(requiredFieldKeys, values);
    if (missing.length > 0) return; // form errors will show inline
    setSubjectData(values);
    nextStep();
    router.push(`/agreement/${id}/steps/evidence`);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
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

      <Button
        title="Next — Evidence"
        variant="primary"
        size="lg"
        fullWidth
        onPress={handleSubmit(onSubmit)}
      />
    </ScrollView>
  );
}
