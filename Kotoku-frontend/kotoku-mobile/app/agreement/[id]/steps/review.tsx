import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { CircleCheckBig, FileText, Image as ImageIcon, Pencil } from "lucide-react-native";
import { Image, Pressable, ScrollView, Text, View } from "react-native";

import { listEvidence, type EvidenceItemResponse } from "@/api/evidence";
import { Button, NoticeCard } from "@/components/ui";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { colors } from "@/theme/tokens";

function formatBytes(value: number | null) {
  if (!value) return "Size unavailable";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return "Date unavailable";
  return new Date(timestamp).toLocaleDateString();
}

export default function ReviewStep() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { scenarioId, partyA, partyB, subjectData, goToStep, prevStep, stepIndex } =
    useAgreementStore();
  const template = useTemplate(scenarioId);
  const [roleA, roleB] = template?.partyRoles ?? ["Party A", "Party B"];
  const agreementId = Number(id);
  const { data: evidence = [], isLoading: evidenceLoading } = useQuery({
    queryKey: ["evidence", agreementId],
    queryFn: () => listEvidence(agreementId),
    enabled: agreementId > 0,
  });
  const evidenceLabels = new Map(
    template?.evidenceRequirements.slots.map((slot) => [slot.id, slot.label]) ?? [],
  );

  const handleNext = () => {
    goToStep(4);
    router.push(`/agreement/${id}/steps/consent?scenarioId=${scenarioId}`);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
      contentContainerStyle={{ paddingBottom: 60 }}
    >
      <View className="gap-md rounded-3xl bg-ink-primary p-lg">
        <View className="flex-row items-start gap-md">
          <View className="h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
            <CircleCheckBig size={22} color="#fff" strokeWidth={1.8} />
          </View>
          <View className="flex-1 gap-xs">
            <Text className="text-[11px] font-semibold uppercase tracking-[2px] text-white/60">
              Step 4
            </Text>
            <Text className="text-xl font-semibold text-white">Review the final record</Text>
            <Text className="text-sm leading-relaxed text-white/75">
              This is the moment to catch anything wrong before consent codes go out and the agreement becomes locked.
            </Text>
          </View>
        </View>
      </View>

      {/* Parties */}
      <Section
        title="Parties"
        onEdit={() => router.push(`/agreement/${id}/steps/parties?scenarioId=${scenarioId}`)}
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
            onEdit={() => router.push(`/agreement/${id}/steps/details?scenarioId=${scenarioId}`)}
          >
            {rows.map((row) => (
              <ReviewRow key={row.label} label={row.label} value={row.value} />
            ))}
          </Section>
        );
      })}

      <Section
        title="Evidence"
        onEdit={() => router.push(`/agreement/${id}/steps/evidence?scenarioId=${scenarioId}`)}
      >
        {evidenceLoading ? (
          <Text className="text-sm text-ink-muted">Loading uploaded evidence…</Text>
        ) : evidence.length > 0 ? (
          <View className="gap-md">
            {evidence.map((item) => (
              <EvidenceReviewCard
                key={item.id}
                item={item}
                label={evidenceLabels.get(item.evidence_type) ?? item.evidence_type}
              />
            ))}
          </View>
        ) : (
          <Text className="text-sm text-ink-muted">
            No confirmed evidence is attached yet.
          </Text>
        )}
      </Section>

      <NoticeCard
        variant="warning"
        title="Next: consent codes"
        body="Once you proceed, the agreement moves into consent and details should no longer be treated as editable. Check names, numbers, dates, and photos carefully now."
        compact
      />

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

function EvidenceReviewCard({
  item,
  label,
}: {
  item: EvidenceItemResponse;
  label: string;
}) {
  const isImage = item.mime_type.startsWith("image/");

  return (
    <View className="rounded-lg border border-border-subtle bg-surface-subtle overflow-hidden">
      <View className="flex-row gap-md p-md">
        <View className="w-20 h-20 rounded-md bg-surface-card items-center justify-center overflow-hidden">
          {isImage && item.view_url ? (
            <Image
              source={{ uri: item.view_url, cache: "force-cache" }}
              className="w-full h-full"
              resizeMode="cover"
            />
          ) : item.file_type === "document" ? (
            <FileText size={24} color={colors.inkMuted} />
          ) : (
            <ImageIcon size={24} color={colors.inkMuted} />
          )}
        </View>
        <View className="flex-1 gap-xs">
          <View className="flex-row items-start justify-between gap-sm">
            <Text className="text-sm font-semibold text-ink-primary flex-1">
              {label}
            </Text>
            <Text className="text-xs font-semibold text-emerald-700">
              Confirmed
            </Text>
          </View>
          <Text className="text-xs text-ink-muted" numberOfLines={1}>
            {item.original_name || item.mime_type || item.file_type}
          </Text>
          <Text className="text-xs text-ink-muted">
            {item.mime_type || item.file_type} · {formatBytes(item.size_bytes)}
          </Text>
          <Text className="text-xs text-ink-muted">
            Added {formatDate(item.created_at)}
          </Text>
          {item.uploaded_by_role && (
            <Text className="text-xs text-ink-muted">
              Uploaded by {item.uploaded_by_role}
            </Text>
          )}
        </View>
      </View>
    </View>
  );
}
