import { useLocalSearchParams, useRouter } from "expo-router";
import { Pencil } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { colors } from "@/theme/tokens";

export default function ReviewStep() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { scenarioId, partyA, partyB, subjectData, nextStep, prevStep, stepIndex } =
    useAgreementStore();
  const template = useTemplate(scenarioId);
  const [roleA, roleB] = template?.partyRoles ?? ["Party A", "Party B"];

  const handleNext = () => {
    nextStep();
    router.push(`/agreement/${id}/steps/consent`);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
      style={{ paddingBottom: 40 }}
    >
      <Text className="text-xl font-semibold text-ink-primary">
        Review your agreement
      </Text>
      <Text className="text-sm text-ink-secondary -mt-md">
        Check all details before requesting consent codes.
      </Text>

      {/* Parties */}
      <Section
        title="Parties"
        onEdit={() => router.push(`/agreement/${id}/steps/parties`)}
      >
        <ReviewRow label={roleA} value={partyA.fullName} />
        <ReviewRow label="Phone" value={partyA.phone} />
        <ReviewRow label="ID" value={`${partyA.idType} — ${partyA.idNumber}`} />
        <View className="h-px bg-border-subtle my-sm" />
        <ReviewRow label={roleB} value={partyB.fullName} />
        <ReviewRow label="Phone" value={partyB.phone} />
        <ReviewRow label="ID" value={`${partyB.idType} — ${partyB.idNumber}`} />
      </Section>

      {/* Agreement details — render each section from the template */}
      {template?.detailSections.map((section) => {
        const rows = section.fields
          .map((key) => {
            const def = template.fields[key];
            const val = subjectData[key];
            if (!def || val === undefined || val === null || val === "") return null;
            return { label: def.label, value: String(val) };
          })
          .filter(Boolean) as { label: string; value: string }[];

        if (rows.length === 0) return null;

        return (
          <Section
            key={section.title}
            title={section.title}
            onEdit={() => router.push(`/agreement/${id}/steps/details`)}
          >
            {rows.map((row) => (
              <ReviewRow key={row.label} label={row.label} value={row.value} />
            ))}
          </Section>
        );
      })}

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
            onPress={handleNext}
          />
        </View>
      </View>
    </ScrollView>
  );
}

// ---------- Sub-components ----------

function Section({
  title,
  onEdit,
  children,
}: {
  title: string;
  onEdit?: () => void;
  children: React.ReactNode;
}) {
  return (
    <View className="bg-surface-card rounded-lg border border-border-subtle overflow-hidden">
      <View className="flex-row items-center justify-between px-lg py-md border-b border-border-subtle">
        <Text className="text-md font-semibold text-ink-primary">{title}</Text>
        {onEdit && (
          <Pressable onPress={onEdit} className="flex-row items-center gap-xs">
            <Pencil size={14} color={colors.brandPrimary} />
            <Text className="text-sm text-brand-primary">Edit</Text>
          </Pressable>
        )}
      </View>
      <View className="px-lg py-md gap-sm">{children}</View>
    </View>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between gap-md">
      <Text className="text-sm text-ink-muted flex-shrink-0">{label}</Text>
      <Text className="text-sm text-ink-primary text-right flex-1" numberOfLines={2}>
        {value}
      </Text>
    </View>
  );
}
